//
// Created by ROG on 2025/12/1.
//
#include "MQ-136.h"
#include "adc.h"
#include <math.h>
float MQ136_ReadAO(uint32_t adc_val) {

    float voltage = 0.0f;

    // 转换为电压（参考电压3.3V）
    voltage = (adc_val * 3.3f) / 4095.0f;

    return voltage;
}

uint8_t MQ136_ReadDO(void) {
    // 读取PC15引脚电平（GPIO_PinState返回0或1）
    return HAL_GPIO_ReadPin(MQ136_DO_PORT, MQ136_DO_PIN);
}

float MQ136_ReadPPM(float mq136_voltage) {
    // MQ-136针对硫化氢的特性参数（最佳拟合）
    float v0 = 0.32f; // 清洁空气中（硫化氢浓度~0ppm）的输出电压（典型值）
    float a = 1000.0f; // 拟合系数A
    float b = -3.0f;   // 拟合系数B（指数）
    float ppm = 0.0f;

    // 最佳拟合公式：基于MQ-136硫化氢特性曲线（ppm = A * (Vout/V0)^B）
    if (mq136_voltage > 0 && v0 > 0) {
        ppm = a * pow((mq136_voltage / v0), b);
    }

    // 限制测量范围（根据传感器规格，通常0-500ppm）
    if (ppm < 0) ppm = 0;
    if (ppm > 500) ppm = 500;

    return ppm;
}
