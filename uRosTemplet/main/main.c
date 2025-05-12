#include <stdio.h>

/* FreeRTOS and ESP-IDF headers */
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_mac.h"

/* micro-ROS headers */
#include <uros_network_interfaces.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

// <||Headers||>

#ifdef CONFIG_MICRO_ROS_ESP_XRCE_DDS_MIDDLEWARE
    #include <rmw_microros/rmw_microros.h>
#endif
#if defined(RMW_UXRCE_TRANSPORT_CUSTOM)
    #include <rmw_microxrcedds_c/config.h>
    #include "esp32_serial_transport.h"
    static uart_port_t uart_port = UART_NUM_0;
#endif

/* Error-checking macros for micro-ROS calls */
#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; \
    if((temp_rc != RCL_RET_OK)) { \
        printf("Failed status on line %d: %d. Aborting.\n", __LINE__, (int)temp_rc); \
        vTaskDelete(NULL); \
    } \
}
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; \
    if((temp_rc != RCL_RET_OK)) { \
        printf("Failed status on line %d: %d. Continuing.\n", __LINE__, (int)temp_rc); \
    } \
}

// <||Variables||>

// <||Callbacks||>

void micro_ros_task(void * arg) {
    rcl_allocator_t allocator = rcl_get_default_allocator();
    rclc_support_t support;

    rcl_init_options_t init_options = rcl_get_zero_initialized_init_options();
	RCCHECK(rcl_init_options_init(&init_options, allocator));

    #if defined(CONFIG_MICRO_ROS_ESP_NETIF_WLAN) || defined(CONFIG_MICRO_ROS_ESP_NETIF_ENET)
        rmw_init_options_t* rmw_options = rcl_init_options_get_rmw_init_options(&init_options);

        // Static Agent IP and port can be used instead of autodisvery.
        RCCHECK(rmw_uros_options_set_udp_address(CONFIG_MICRO_ROS_AGENT_IP, CONFIG_MICRO_ROS_AGENT_PORT, rmw_options));
        //RCCHECK(rmw_uros_discover_agent(rmw_options));
    #endif

	// create init_options
	RCCHECK(rclc_support_init_with_options(&support, 0, NULL, &init_options, &allocator));


    /* Create a micro-ROS node */
    rcl_node_t node;
    RCCHECK(rclc_node_init_default(&node, "<||Nodename||>", "<||Namespace||>", &support));


    rclc_executor_t executor;
    RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
    // <||AddCallbacks||>

    while (1) {        
        /* Process any incoming micro-ROS messages */
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
        vTaskDelay(pdMS_TO_TICKS(10));
        // <||ExamplePublish||>
    }

}

void app_main(void)
{
    #if defined(RMW_UXRCE_TRANSPORT_CUSTOM)
    rmw_uros_set_custom_transport(
        true,
        (void *) &uart_port,
        esp32_serial_open,
        esp32_serial_close,
        esp32_serial_write,
        esp32_serial_read
    );
    #elif defined(CONFIG_MICRO_ROS_ESP_NETIF_WLAN) || defined(CONFIG_MICRO_ROS_ESP_NETIF_ENET)
        ESP_ERROR_CHECK(uros_network_interface_initialize());
    #else
        #error micro-ROS transports misconfigured
    #endif  

    // Create micro-ROS task pinned to core 1
    xTaskCreate(
        micro_ros_task,                    // Task function.
        "uros_task",                       // Name of the task.
        CONFIG_MICRO_ROS_APP_STACK,        // Stack size.
        NULL,                              // Parameter.
        CONFIG_MICRO_ROS_APP_TASK_PRIO,    // Priority.
        NULL                               // Task handle (not used).
    );

    // <||Tasks||>
}