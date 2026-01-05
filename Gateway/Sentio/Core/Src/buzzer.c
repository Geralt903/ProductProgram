//
// Created by ROG on 2025/12/2.
//
#include "buzzer.h"
#include "stm32f1xx_hal.h"

void Buzzer_On(int8_t times) {
    HAL_GPIO_WritePin(Buzzer_GPIO_Port, Buzzer_Pin, GPIO_PIN_RESET);
    HAL_Delay(times);
    HAL_GPIO_WritePin(Buzzer_GPIO_Port, Buzzer_Pin, GPIO_PIN_SET);
}