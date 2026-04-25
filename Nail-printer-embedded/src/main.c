#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "printcart_buffer_filler.h"
#include "printcart_genwaveform.h"
#include "printcart_i2s.h"

// Define cartridge type
#define CART_IS_COLOR 1

// GPIO numbers for the lines that are connected to the printer cartridge.
#define PIN_NUM_CART_D2 12
#define PIN_NUM_CART_D1 27
#define PIN_NUM_CART_D3 13
#define PIN_NUM_CART_CSYNC 14
#define PIN_NUM_CART_S2 32
#define PIN_NUM_CART_S4 2
#define PIN_NUM_CART_S1 4
#define PIN_NUM_CART_S5 5
#define PIN_NUM_CART_DCLK 18
#define PIN_NUM_CART_S3 19
#define PIN_NUM_CART_F3 15
#define PIN_NUM_CART_F5 21

// UART Configuration for RPi communication via USB/Serial
#define UART_NUM UART_NUM_0
#define BUF_SIZE (1024)

// Protocol constants
#define CMD_START_PRINT 0x01
#define CMD_READY       0x02
#define CMD_SEND_LINE   0x03
#define CMD_LINE_ACK    0x04
#define CMD_HOME        0x05

#define WAVEFORM_DMALEN 1500

QueueHandle_t nozdata_queue;

void printcart_init() {
    // Create nozzle data queue
    nozdata_queue = xQueueCreate(10, PRINTCART_NOZDATA_SZ);
    
    // Initialize I2S parallel device for printer cartridge.
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
    i2s_parallel_setup(&I2S1, &i2scfg);
    i2s_parallel_start(&I2S1);
    
#ifdef CART_IS_COLOR
    printcart_select_waveform(PRINTCART_WAVEFORM_COLOR_B);
#endif

    printf("Printcart driver inited (I2S Parallel)\n");
}

void uart_init() {
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
    uart_driver_install(UART_NUM, BUF_SIZE * 2, 0, 0, NULL, 0);
    printf("UART communication with Open-Nail-Printer initialized\n");
}

void mainloop(void *arg) {
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
                        xQueueSend(nozdata_queue, line_buffer, portMAX_DELAY);
                        // Send ACK
                        uint8_t tx = CMD_LINE_ACK;
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

void app_main(void) {
    printcart_init();
    uart_init();
    
    xTaskCreatePinnedToCore(mainloop, "mainloop", 1024 * 4, NULL, 7, NULL, 1);
}
