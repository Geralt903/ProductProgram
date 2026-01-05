//
// Created by ROG on 2025/12/2.
//

#ifndef BUZZER_H
#define BUZZER_H

#include "stm32f1xx_hal.h"

// 引脚定义
#define Buzzer_Pin GPIO_PIN_9
#define Buzzer_GPIO_Port GPIOB

void Buzzer_On(int8_t times);

#endif //BUZZER_H
