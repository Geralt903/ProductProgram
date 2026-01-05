//
// Created by ROG on 2025/11/23.
//

#include "MQ-4.h"
#include <math.h>
#include "adc.h"

extern ADC_HandleTypeDef hadc1;  // 引用ADC1句柄（在adc.c中定义）

/**
 * @brief 初始化MQ-4模块
 *        （AO已通过ADC1初始化，此处主要确保DO引脚配置正确）
 */
void MQ4_Init(void) {
    if (hadc1.State == HAL_ADC_STATE_RESET) {
        MX_ADC1_Init();
    }
    if (HAL_ADC_GetState(&hadc1) != HAL_ADC_STATE_READY) {
        HAL_ADC_Start(&hadc1);
    }
}

/**
 * @brief 读取MQ-4 AO引脚的模拟值（转换为电压）
 * @return 电压值（单位：V）
 */
float MQ4_ReadAO(uint32_t adc_val) {

    float voltage = 0.0f;

    // 转换为电压（参考电压3.3V）
    voltage = (adc_val * 3.3f) / 4095.0f;

    return voltage;
}

/**
 * @brief 读取MQ-4 DO引脚的数字状态
 * @return 0：低电平（浓度低于阈值），1：高电平（浓度高于阈值）
 */
uint8_t MQ4_ReadDO(void) {
    // 读取PC15引脚电平（GPIO_PinState返回0或1）
    return HAL_GPIO_ReadPin(MQ4_DO_PORT, MQ4_DO_PIN);
}

float MQ4_ReadPPM(float mq4_voltage) {
    // MQ-4针对甲烷的特性参数（最佳拟合）
    float v0 = 0.40f; // 清洁空气中（甲烷浓度~0ppm）的输出电压（典型值）
    float a = 6000.0f; // 拟合系数A
    float b = -2.5f;   // 拟合系数B（指数）
    float ppm = 0.0f;

    // 最佳拟合公式：基于MQ-4甲烷特性曲线（ppm = A * (Vout/V0)^B）
    if (mq4_voltage > 0 && v0 > 0) {
        ppm = a * pow((mq4_voltage / v0), b);
    }

    // 限制测量范围（根据传感器规格，通常0-10000ppm）
    if (ppm < 0) ppm = 0;
    if (ppm > 10000) ppm = 10000;

    return ppm;
}