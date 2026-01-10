/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "adc.h"
#include "dma.h"
#include "i2c.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "hcsr04.h"
#include "aht20.h"
#include "MQ-4.h"
#include "MQ-136.h"
#include "buzzer.h"
#include "lora_Operation.h"
#include "stdio.h"
#include "string.h"
#include "DeviceIDconf.h"  // 需要包含这个文件来使用 DeviceID_Write 和 DeviceID_Read

#include "stdbool.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

uint32_t values[4];
uint8_t ADCmsg[100];
uint32_t DeviceID = 0;
volatile uint32_t g_device_id_live = 0;
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_I2C1_Init();
  MX_TIM1_Init();
  MX_USART3_UART_Init();
  /* USER CODE BEGIN 2 */
  AHT20_Init();
  HCSR04_Init(&htim1, TIM_CHANNEL_3, TIM_CHANNEL_4);

  HAL_ADCEx_Calibration_Start(&hadc1);
  HAL_ADC_Start_DMA(&hadc1,values,4);
  HAL_GPIO_WritePin(EN_GPIO_Port,EN_Pin,GPIO_PIN_SET);

  if (!DeviceID_Read(&DeviceID)) {
    DeviceID = 0x12345678u;
    DeviceID_Write(DeviceID);
  }
  g_device_id_live = DeviceID;


  uint32_t i=0;//test
  //Buzzer_On(100);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    i++;
    g_UserIDConfig.userID=i;
    g_device_id_live = g_UserIDConfig.userID;

    HCSR04_GetDistance(&htim1);
    
    AHT20_Measure();

    //CH1=MQ4 CH2=MQ136 CH3=Vbat CH4=InternalTemp
    sprintf(ADCmsg, "ADC DMA Complete: CH1=%d, CH2=%d, CH3=%d, CH4=%d\r\n",
            values[0], values[1], values[2], values[3]);

    //HAL_UART_Transmit(&huart3, ADCmsg, strlen((char*)ADCmsg),500);

    send_to_lora(&huart3, ADCmsg, strlen((char*)ADCmsg));

    HAL_Delay(500);
    float temperature = AHT20_Temperature();
    float humidity = AHT20_Humidity();

    float mq4_voltage = MQ4_ReadAO(values[0]);       // 读取mq4AO电压
    float mq4_ppm = MQ4_ReadPPM(mq4_voltage);   // 读取甲烷浓度（ppm）
    uint8_t mq4_do_state = MQ4_ReadDO();      // 读取mq4DO状态

    float mq136_voltage = MQ136_ReadAO(values[1]);       // 读取mq136AO电压
    float mq136_ppm = MQ136_ReadPPM(mq136_voltage);   // 读取浓度（ppm）
    uint8_t mq136_do_state = MQ136_ReadDO();      // 读取mq136DO状态

    uint8_t buffer[500];
    int len = snprintf((char*)buffer, sizeof(buffer),
                       "Distance: %.2f cm \rTemperature: %.2f C  Humidity: %.2f %%\rMQ-4 AO: %.2f V\rMQ-4 PPM: %.2f ppm\rMQ-4 DO: %d\rMQ-136 AO: %.2f V\rMQ-136 PPM: %.2f ppm\rMQ-136 DO: %d\r\n",
                       distance, temperature, humidity,mq4_voltage, mq4_ppm, mq4_do_state ,mq136_voltage, mq136_ppm, mq136_do_state
                       );

   // HAL_UART_Transmit(&huart3, buffer, len, 500);
    send_to_lora(&huart3, buffer, len);

HAL_Delay(1000);
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
  PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV6;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
    Buzzer_On(200);
    HAL_Delay(1000);
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
