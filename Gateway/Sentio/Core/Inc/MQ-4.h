//
// Created by ROG on 2025/11/23.
//

#ifndef MQ_4_H
#define MQ_4_H

#include "stm32f1xx_hal.h"

// MQ-4 DO引脚定义（PA3）
#define MQ4_DO_PORT GPIOA
#define MQ4_DO_PIN  GPIO_PIN_3

// 函数声明
void MQ4_Init(void);                     // 初始化MQ-4模块
float MQ4_ReadAO(uint32_t adc_val);                  // 读取AO模拟值（电压）
uint8_t MQ4_ReadDO(void);                // 读取DO数字状态（0/1）
float MQ4_ReadPPM(float mq4_voltage); // 读取甲烷浓度（ppm）
#endif //MQ_4_H