#include "stm32f1xx_hal.h"
#include "lora_Operation.h"


// 发送数据到 LoRa 的函数
int send_to_lora(UART_HandleTypeDef *usart, uint8_t *data, uint16_t len)
{
    // 调用 HAL 库的串口发送函数，500 毫秒超时
    if (detect_occupied(AUX_GPIO_Port,AUX_Pin)==GPIO_PIN_SET)
    {
        HAL_UART_Transmit(usart, "Device LORA Occupied", len, 0xFFFF);
        return 1;
    }
    if (HAL_UART_Transmit(usart, data, len, 500) == HAL_OK)
        return 1;  // 返回 1 表示正常发送成功
    else
        return 0;  // 返回 0 表示发送失败
}

// 检测 GPIO 引脚是否被占用的函数
int detect_occupied(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin)
{
    // 读取指定 GPIO 引脚的电平状态
    GPIO_PinState pinState = HAL_GPIO_ReadPin(GPIOx, GPIO_Pin);

    // 判断引脚状态
    if (pinState == GPIO_PIN_SET)
    {
        // 引脚是高电平，表示占用
        return 1;  // 返回 1 表示引脚占用
    }
    else
    {
        // 引脚是低电平，表示未占用
        return 0;  // 返回 0 表示引脚未占用
    }
}
