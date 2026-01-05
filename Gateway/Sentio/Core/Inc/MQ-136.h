//
// Created by ROG on 2025/12/1.
//

#ifndef MQ_136_H
#define MQ_136_H

#include "stm32f1xx_hal.h"

// MQ-136 DO引脚定义（PA4）
#define MQ136_DO_PORT GPIOA
#define MQ136_DO_PIN  GPIO_PIN_4

float MQ136_ReadAO(uint32_t adc_val);                  // 读取AO模拟值（电压）
uint8_t MQ136_ReadDO(void);                // 读取DO数字状态（0/1）
float MQ136_ReadPPM(float mq4_voltage); // 读取甲烷浓度（ppm）

#endif //MQ_136_H
