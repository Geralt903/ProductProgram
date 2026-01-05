/*
 * hcsr04.h
 *
 *  Created on: Nov 10, 2025
 *      Author: ROG
 */

#ifndef INC_HCSR04_H_
#define INC_HCSR04_H_

// 全局变量声明（仅声明，不定义）
extern volatile int upedge;
extern volatile int downedge;
extern volatile float distance;


// 函数声明（匹配.c文件实现）
void HCSR04_Init(TIM_HandleTypeDef *htim, uint32_t ch_rise, uint32_t ch_fall);
void HCSR04_GetDistance(TIM_HandleTypeDef *htim);

#endif /* INC_HCSR04_H_ */
