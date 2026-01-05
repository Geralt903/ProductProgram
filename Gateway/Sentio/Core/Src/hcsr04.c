/*
 * hcsr04.c
 *
 *  Created on: Nov 10, 2025
 *      Author: ROG
 */
#include "main.h"

/* 全局变量定义（带volatile，仅在.c文件中定义） */
volatile int upedge = 0;
volatile int downedge = 0;
volatile float distance = 0.0f;

/* 初始化：传入定时器句柄与用于上升/下降捕获的通道 */
void HCSR04_Init(TIM_HandleTypeDef *htim, uint32_t ch_rise, uint32_t ch_fall)
{
    // 检查定时器句柄是否为NULL
    if (htim == NULL) {
        Error_Handler();  // 使用系统错误处理函数
        return;
    }

    /* 启动定时器基时钟和输入捕获中断（上升/下降通道） */
    HAL_TIM_Base_Start(htim);
    HAL_TIM_IC_Start_IT(htim, ch_rise);
    HAL_TIM_IC_Start_IT(htim, ch_fall);
}

/* 触发并读取距离（假定定时器每计数为1us） */
void HCSR04_GetDistance(TIM_HandleTypeDef *htim)
{
    // 检查定时器句柄是否为NULL
    if (htim == NULL) {
        distance = -2.0f;  // 用特定值标识参数错误
        return;
    }

    upedge = 0;
    downedge = 0;

    /* 清计数器 */
    __HAL_TIM_SET_COUNTER(htim, 0);

    /* 触发10us脉冲（原代码用了1ms，此处修正为微秒级延时） */
    HAL_GPIO_WritePin(Trig_GPIO_Port, Trig_Pin, GPIO_PIN_SET);
    // 注意：需实现微秒延时函数（如delay_us(10)），HAL_Delay是毫秒级
    HAL_Delay(1);  //实际应改为微秒延时
    HAL_GPIO_WritePin(Trig_GPIO_Port, Trig_Pin, GPIO_PIN_RESET);

    /* 等待上升和下降捕获，带超时保护（100ms） */
    uint32_t start = HAL_GetTick();
    while (upedge == 0 && (HAL_GetTick() - start) < 100) { }
    start = HAL_GetTick();
    while (downedge == 0 && (HAL_GetTick() - start) < 100) { }

    if (upedge != 0 && downedge != 0)
    {
        int32_t diff = downedge - upedge;
        /* 考虑计数器回绕（假设自动重装载值可读） */
        uint32_t arr = __HAL_TIM_GET_AUTORELOAD(htim);
        if (diff < 0) diff += (int32_t)arr + 1;

        /* 若定时器每刻度为1us，公式为：distance_cm = (pulse_us * 0.034) / 2 */
        distance = ((float)diff * 0.034f) / 2.0f;
    }
    else
    {
        distance = -1.0f; /* 表示超时或无效 */
    }
}

/* 在HAL的输入捕获回调中设置边沿时间（放在用户代码区） */
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
    // 新增：检查定时器句柄是否为NULL
    if (htim == NULL) {
        return;
    }

    /* HAL提供htim->Channel标识当前触发的通道 */
    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_3)
    {
        upedge = (int)HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_3);
    }
    else if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_4)
    {
        downedge = (int)HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_4);
    }
}
