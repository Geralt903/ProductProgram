//
// Created by 1 on 2026/1/5.
//

#ifndef PRODUCTPROGRAM_LORA_PIN_H
#define PRODUCTPROGRAM_LORA_PIN_H
#include "stm32f1xx_hal.h"
#define EN_Pin GPIO_PIN_1
#define AUX_Pin GPIO_PIN_0
#define AUX_GPIO_Port GPIOB
#define EN_GPIO_Port GPIOB
int send_to_lora(UART_HandleTypeDef *usart, uint8_t *data, uint16_t len);
int detect_occupied(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);


#endif //PRODUCTPROGRAM_LORA_PIN_H