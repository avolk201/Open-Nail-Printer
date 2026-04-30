#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/ringbuf.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "driver/pulse_cnt.h"
#include "driver/mcpwm_prelude.h"
#include "printcart_buffer_filler.h"
#include "printcart_genwaveform.h"
#include "printcart_i2s.h"

// Define cartridge type
#define CART_IS_COLOR 1

// GPIO numbers for the lines that are connected to the printer cartridge.
#define PIN_NUM_CART_D1 22
#define PIN_NUM_CART_D2 21
#define PIN_NUM_CART_D3 19
#define PIN_NUM_CART_CSYNC 13
#define PIN_NUM_CART_S1 18
#define PIN_NUM_CART_S2 5
#define PIN_NUM_CART_S3 17
#define PIN_NUM_CART_S4 16
#define PIN_NUM_CART_S5 4
#define PIN_NUM_CART_DCLK 23
#define PIN_NUM_CART_F3 27
#define PIN_NUM_CART_F5 14

// UART Configuration for RPi communication via USB/Serial
#define UART_NUM UART_NUM_0
#define BUF_SIZE (4096) // Increased for robust ringbuffer ingestion

// UART Configuration for TMC2209
#define TMC_UART_NUM UART_NUM_1
#define TMC_TX_PIN 15
#define TMC_RX_PIN 15 // Single-wire UART shared

// Encoder Pins
#define ENCODER_PIN_A 36
#define ENCODER_PIN_B 39

// Limit Switch Pins
#define LIMIT_X_PIN 34
#define LIMIT_Y_PIN 35

// Stepper Motor Pins
#define MOTOR_X_STEP_PIN 32
#define MOTOR_X_DIR_PIN  33
#define MOTOR_Y_STEP_PIN 25
#define MOTOR_Y_DIR_PIN  26
#define MOTOR_Z_STEP_PIN -1 // Not used in this hardware
#define MOTOR_Z_DIR_PIN  -1
#define MOTOR_ENABLE_PIN 12

// Protocol constants
#define CMD_START_PRINT 0x01
#define CMD_READY       0x02
#define CMD_SEND_LINE   0x03
#define CMD_LINE_ACK    0x04
#define CMD_HOME        0x05
#define CMD_LINE_NACK   0x06

#define WAVEFORM_DMALEN 1500

typedef struct {
    int target_x;
    int target_y;
    int target_z;
    uint32_t speed_hz;
} motion_cmd_t;

QueueHandle_t nozdata_queue;
RingbufHandle_t uart_rx_ringbuf;
QueueHandle_t motion_queue;

mcpwm_timer_handle_t x_timer = NULL;
mcpwm_oper_handle_t x_oper = NULL;
mcpwm_cmpr_handle_t x_cmpr = NULL;
mcpwm_gen_handle_t x_gen = NULL;

// Interrupt Service Routine for Limit Switches
static void IRAM_ATTR limit_switch_isr_handler(void* arg) {
    uint32_t gpio_num = (uint32_t) arg;
    // Handle homing sequence interrupt
}

void tmc2209_init() {
    // TMC2209 Interfacing: UART configuration for stealthChop, microstepping, and motor current.
    uart_config_t tmc_uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    uart_param_config(TMC_UART_NUM, &tmc_uart_config);
    uart_set_pin(TMC_UART_NUM, TMC_TX_PIN, TMC_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(TMC_UART_NUM, 1024, 0, 0, NULL, 0);
    printf("TMC2209 UART initialized\n");
    
    // Set parameters over UART (Pseudo-code for TMC2209 setup)
    // tmc2209_write_reg(TMC_UART_NUM, TMC2209_REG_GCONF, 0x00000008); // Enable stealthChop
    // tmc2209_write_reg(TMC_UART_NUM, TMC2209_REG_IHOLD_IRUN, 0x000F1008); // Set motor currents
}

void motion_init() {
    // Step/Dir Generation: ESP32 MCPWM peripheral for smooth acceleration/deceleration.
    printf("Initializing Motion Control MCPWM...\n");
    
    motion_queue = xQueueCreate(10, sizeof(motion_cmd_t));

    // Setup DIR and ENABLE pins
    gpio_config_t dir_conf = {
        .intr_type = GPIO_INTR_DISABLE,
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = (1ULL<<MOTOR_X_DIR_PIN) | (1ULL<<MOTOR_Y_DIR_PIN) | (1ULL<<MOTOR_ENABLE_PIN),
        .pull_down_en = 0,
        .pull_up_en = 0
    };
    gpio_config(&dir_conf);
    gpio_set_level(MOTOR_ENABLE_PIN, 0); // Enable drivers (typically active low)

    // X-Axis MCPWM timer for generating Step Pulses
    mcpwm_timer_config_t timer_config = {
        .group_id = 0,
        .clk_src = MCPWM_TIMER_CLK_SRC_DEFAULT,
        .resolution_hz = 1000000, // 1MHz, 1us per tick
        .period_ticks = 1000,     // Initial 1kHz step rate
        .count_mode = MCPWM_TIMER_COUNT_MODE_UP,
    };
    mcpwm_new_timer(&timer_config, &x_timer);

    mcpwm_operator_config_t oper_config = {
        .group_id = 0, // same as timer
    };
    mcpwm_new_operator(&oper_config, &x_oper);
    mcpwm_operator_connect_timer(x_oper, x_timer);

    mcpwm_comparator_config_t cmpr_config = {
        .flags.update_cmp_on_tez = true,
    };
    mcpwm_new_comparator(x_oper, &cmpr_config, &x_cmpr);
    
    // Set 50% duty cycle initially
    mcpwm_comparator_set_compare_value(x_cmpr, 500); 

    mcpwm_generator_config_t gen_config = {
        .gen_gpio_num = MOTOR_X_STEP_PIN,
    };
    mcpwm_new_generator(x_oper, &gen_config, &x_gen);

    // Generator actions: go high at timer zero, go low at compare match (50% duty pulse)
    mcpwm_generator_set_action_on_timer_event(x_gen, 
        MCPWM_GEN_TIMER_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP, MCPWM_TIMER_EVENT_EMPTY, MCPWM_GEN_ACTION_HIGH));
    mcpwm_generator_set_action_on_compare_event(x_gen, 
        MCPWM_GEN_COMPARE_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP, x_cmpr, MCPWM_GEN_ACTION_LOW));

    mcpwm_timer_enable(x_timer);
    
    printf("Motion Control MCPWM initialized for X-Axis\n");
}

void homing_init() {
    // Homing Sequence: Limit switch interrupts prior to printing.
    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_NEGEDGE,
        .pin_bit_mask = (1ULL << LIMIT_X_PIN) | (1ULL << LIMIT_Y_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = 1,
    };
    gpio_config(&io_conf);
    
    gpio_install_isr_service(0);
    gpio_isr_handler_add(LIMIT_X_PIN, limit_switch_isr_handler, (void*) LIMIT_X_PIN);
    gpio_isr_handler_add(LIMIT_Y_PIN, limit_switch_isr_handler, (void*) LIMIT_Y_PIN);
    printf("Homing interrupts initialized\n");
}

void pcnt_encoder_init() {
    // Absolute Positioning (PCNT): Configure ESP32 PCNT to read 150 LPI optical encoder.
    pcnt_unit_config_t unit_config = {
        .high_limit = 10000,
        .low_limit = -10000,
    };
    pcnt_unit_handle_t pcnt_unit = NULL;
    pcnt_new_unit(&unit_config, &pcnt_unit);

    pcnt_glitch_filter_config_t filter_config = {
        .max_glitch_ns = 1000,
    };
    pcnt_unit_set_glitch_filter(pcnt_unit, &filter_config);

    pcnt_chan_config_t chan_a_config = {
        .edge_gpio_num = ENCODER_PIN_A,
        .level_gpio_num = ENCODER_PIN_B,
    };
    pcnt_channel_handle_t pcnt_chan_a = NULL;
    pcnt_new_channel(pcnt_unit, &chan_a_config, &pcnt_chan_a);

    pcnt_channel_set_edge_action(pcnt_chan_a, PCNT_CHANNEL_EDGE_ACTION_DECREASE, PCNT_CHANNEL_EDGE_ACTION_INCREASE);
    pcnt_channel_set_level_action(pcnt_chan_a, PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_INVERSE);

    pcnt_unit_enable(pcnt_unit);
    pcnt_unit_clear_count(pcnt_unit);
    pcnt_unit_start(pcnt_unit);
    
    // TODO: Create a watchpoint interrupt or hardware trigger that links PCNT threshold to I2S DMA output.
    printf("PCNT Encoder initialized\n");
}

void printcart_init() {
    // Create nozzle data queue
    nozdata_queue = xQueueCreate(10, PRINTCART_NOZDATA_SZ);
    
    // Initialize I2S DMA across 12 GPIO pins simultaneously.
    i2s_parallel_config_t i2scfg = {
        .gpio_bus = {
            PIN_NUM_CART_D1, //0
            PIN_NUM_CART_D2, //1
            PIN_NUM_CART_D3, //2
            PIN_NUM_CART_CSYNC, //3
            PIN_NUM_CART_S2, //4
            PIN_NUM_CART_S4, //5
            PIN_NUM_CART_S1, //6
            PIN_NUM_CART_S5, //7
            PIN_NUM_CART_DCLK, //8
            PIN_NUM_CART_S3, //9
            PIN_NUM_CART_F3, //10
            PIN_NUM_CART_F5, //11
            -1, -1, -1, -1 //12-15 - unused
        },
        .bits = I2S_PARALLEL_BITS_16,
        .clkspeed_hz = 3333333, //3.3MHz
        .bufsz = WAVEFORM_DMALEN * sizeof(uint16_t),
        .refill_cb = printcart_buffer_filler_fn,
        .refill_cb_arg = nozdata_queue
    };
    // Ensure the DMA descriptors are tightly synchronized with the encoder pulses
    // so ink is deposited exactly on the grid, regardless of gantry speed fluctuations.
    i2s_parallel_setup(&I2S1, &i2scfg);
    i2s_parallel_start(&I2S1);
    
#ifdef CART_IS_COLOR
    printcart_select_waveform(PRINTCART_WAVEFORM_COLOR_B);
#endif

    printf("Printcart driver inited (I2S Parallel)\n");
}

void uart_init() {
    // Robust ringbuffer is handled by the ESP-IDF UART driver internally when sizing > 0
    uart_config_t uart_config = {
        .baud_rate = 921600,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    // Using UART0 which is typically the default serial connected via USB to RPi
    uart_param_config(UART_NUM, &uart_config);
    uart_set_pin(UART_NUM, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    // Large RX buffer to ingest 921,600 baud data without dropping frames
    uart_driver_install(UART_NUM, BUF_SIZE, 0, 0, NULL, 0); 
    
    // Also create a FreeRTOS ringbuffer if we need to manually queue items further
    uart_rx_ringbuf = xRingbufferCreate(BUF_SIZE, RINGBUF_TYPE_BYTEBUF);
    
    printf("UART communication with Open-Nail-Printer initialized\n");
}

void uart_rx_task(void *arg) {
    uint8_t rx_byte;
    uint8_t line_buffer[PRINTCART_NOZDATA_SZ];
    
    while (1) {
        int len = uart_read_bytes(UART_NUM, &rx_byte, 1, portMAX_DELAY);
        if (len > 0) {
            switch (rx_byte) {
                case CMD_START_PRINT: {
                    xQueueReset(nozdata_queue);
                    uint8_t tx = CMD_READY;
                    uart_write_bytes(UART_NUM, (const char*)&tx, 1);
                    break;
                }
                case CMD_SEND_LINE: {
                    // Wait for exactly PRINTCART_NOZDATA_SZ bytes
                    int bytes_read = 0;
                    while (bytes_read < PRINTCART_NOZDATA_SZ) {
                        int r = uart_read_bytes(UART_NUM, line_buffer + bytes_read, PRINTCART_NOZDATA_SZ - bytes_read, pdMS_TO_TICKS(100));
                        if (r > 0) {
                            bytes_read += r;
                        } else {
                            break; // timeout
                        }
                    }
                    if (bytes_read == PRINTCART_NOZDATA_SZ) {
                        // Queue the data for I2S output to Cartridge
                        // Don't block forever, if queue full send NACK
                        if (xQueueSend(nozdata_queue, line_buffer, pdMS_TO_TICKS(10)) == pdTRUE) {
                            // Send ACK
                            uint8_t tx = CMD_LINE_ACK;
                            uart_write_bytes(UART_NUM, (const char*)&tx, 1);
                        } else {
                            // Queue full, send NACK
                            uint8_t tx = CMD_LINE_NACK;
                            uart_write_bytes(UART_NUM, (const char*)&tx, 1);
                        }
                    } else {
                        // Timeout reading, send NACK
                        uint8_t tx = CMD_LINE_NACK;
                        uart_write_bytes(UART_NUM, (const char*)&tx, 1);
                    }
                    break;
                }
                case CMD_HOME: {
                    // Implement homing if applicable
                    uint8_t tx = CMD_READY;
                    uart_write_bytes(UART_NUM, (const char*)&tx, 1);
                    break;
                }
            }
        }
    }
}

void motion_control_task(void *arg) {
    // This task handles Gantry Implementation & Motion Control
    motion_cmd_t cmd;
    while (1) {
        if (xQueueReceive(motion_queue, &cmd, portMAX_DELAY) == pdTRUE) {
            // Process motion command
            // 1. Set Directions
            gpio_set_level(MOTOR_X_DIR_PIN, cmd.target_x > 0 ? 1 : 0);
            gpio_set_level(MOTOR_Y_DIR_PIN, cmd.target_y > 0 ? 1 : 0);
            
            // 2. Configure speed (simplified, assuming X is primary axis)
            if (cmd.speed_hz > 0) {
                // Generate steps using MCPWM
                mcpwm_timer_start_stop(x_timer, MCPWM_TIMER_START_NO_STOP);
                
                // Placeholder: Wait for encoder/steps to reach target
                // In a full implementation, the PCNT would trigger a stop or interrupt.
                vTaskDelay(pdMS_TO_TICKS(100)); 
                
                // 3. Stop motion
                mcpwm_timer_start_stop(x_timer, MCPWM_TIMER_STOP_EMPTY);
            }
        }
    }
}

void printhead_sync_task(void *arg) {
    // This task monitors the PCNT thresholds and links them to the I2S DMA output
    while (1) {
        // Implement tight synchronization with encoder pulses
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

void app_main(void) {
    // Hardware setup
    uart_init();
    printcart_init();
    tmc2209_init();
    motion_init();
    homing_init();
    pcnt_encoder_init();
    
    // Dual-Core Task Pinning
    
    // Core 0: Pin the UART receiving task to Core 0 to ingest the 921,600 baud data.
    xTaskCreatePinnedToCore(uart_rx_task, "uart_rx_task", 4096, NULL, 10, NULL, 0);
    
    // Core 1: Pin the Motion Control and Printhead Sync tasks to Core 1.
    xTaskCreatePinnedToCore(motion_control_task, "motion_control_task", 4096, NULL, 9, NULL, 1);
    xTaskCreatePinnedToCore(printhead_sync_task, "printhead_sync_task", 4096, NULL, 10, NULL, 1);
}
