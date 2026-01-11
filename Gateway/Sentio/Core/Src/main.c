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
uint32_t DeviceID = 0;
volatile uint32_t g_device_id_live = 0;

#define LORA_PAYLOAD_LEN 16u

static uint16_t scale_clamp_u16(float value, float scale)
{
  float scaled = value * scale;

  if (scaled <= 0.0f) {
    return 0u;
  }
  if (scaled >= 65535.0f) {
    return 65535u;
  }
  return (uint16_t)(scaled + 0.5f);
}

static void pack_u16_be(uint8_t *dst, uint16_t value)
{
  dst[0] = (uint8_t)(value >> 8);
  dst[1] = (uint8_t)value;
}

static void pack_u32_be(uint8_t *dst, uint32_t value)
{
  dst[0] = (uint8_t)(value >> 24);
  dst[1] = (uint8_t)(value >> 16);
  dst[2] = (uint8_t)(value >> 8);
  dst[3] = (uint8_t)value;
}

static void build_lora_payload(uint8_t *payload,
                               uint32_t device_id,
                               float temperature,
                               float humidity,
                               float distance_cm,
                               float mq4_ppm,
                               float mq136_ppm)
{
  uint16_t temperature_u = scale_clamp_u16(temperature, 100.0f);
  uint16_t humidity_u = scale_clamp_u16(humidity, 100.0f);
  uint16_t distance_u = scale_clamp_u16(distance_cm, 10.0f);
  uint16_t mq4_u = scale_clamp_u16(mq4_ppm, 10.0f);
  uint16_t mq136_u = scale_clamp_u16(mq136_ppm, 10.0f);

  memset(payload, 0, LORA_PAYLOAD_LEN);
  pack_u32_be(payload + 0, device_id);
  pack_u16_be(payload + 4, temperature_u);
  pack_u16_be(payload + 6, humidity_u);
  pack_u16_be(payload + 8, distance_u);
  pack_u16_be(payload + 10, mq4_u);
  pack_u16_be(payload + 12, mq136_u);
  payload[14] = 0u;
  payload[15] = 0u;
}
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

    HAL_Delay(500);
    float temperature = AHT20_Temperature();
    float humidity = AHT20_Humidity();

    float mq4_ppm = MQ4_ReadPPM(MQ4_ReadAO(values[0]));
    float mq136_ppm = MQ136_ReadPPM(MQ136_ReadAO(values[1]));

    uint8_t payload[LORA_PAYLOAD_LEN];
    build_lora_payload(payload, g_device_id_live, temperature, humidity, distance, mq4_ppm, mq136_ppm);
    send_to_lora(&huart3, payload, LORA_PAYLOAD_LEN);
    if (HAL_GPIO_ReadPin(AUX_GPIO_Port, GPIO_PIN_0) == GPIO_PIN_RESET) {
      send_to_lora(&huart3, (uint8_t *)"0", 1);  // 如果引脚为低电平（0），发送 0
    } else {
      send_to_lora(&huart3, (uint8_t *)"1", 1);  // 如果引脚为高电平（1），发送 1
    }

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
