#include "DeviceIDconf.h"
#include "stmflash.h"  // 确保 STM32 的 Flash 读写函数可用
#include "main.h"
#include <stdio.h>

#define DEVICE_ID_FLASH_ADDR FLASH_SAVE_ADDR   // 定义设备 ID 存储地址
#define DEVICE_ID_MAGIC 0xABCD  // 用户 ID 存储的魔数，确保数据有效
#define DEVICE_ID_VERSION 1     // 版本号
#define DEVICE_ID_WORDS 5       // 存储的单元数量（魔数 + 版本号 + ID + 校验和）

// 校验和函数：用于验证用户 ID 数据的完整性
static uint16_t DeviceID_Checksum(uint16_t id_low, uint16_t id_high)
{
    return (uint16_t)(DEVICE_ID_MAGIC ^ DEVICE_ID_VERSION ^ id_low ^ id_high);
}

// ============================ 用户 ID 写入 ============================
void DeviceID_Write(uint32_t device_id)
{
    uint16_t id_low = (uint16_t)(device_id & 0xFFFFu);    // 获取设备 ID 低 16 位
    uint16_t id_high = (uint16_t)((device_id >> 16) & 0xFFFFu);  // 获取设备 ID 高 16 位
    uint16_t buf[DEVICE_ID_WORDS];

    buf[0] = DEVICE_ID_MAGIC;           // 存储魔数
    buf[1] = DEVICE_ID_VERSION;         // 存储版本号
    buf[2] = id_low;                    // 存储设备 ID 低 16 位
    buf[3] = id_high;                   // 存储设备 ID 高 16 位
    buf[4] = DeviceID_Checksum(id_low, id_high);  // 存储校验和

    // 将数据写入 Flash
    STMFLASH_Write(DEVICE_ID_FLASH_ADDR, buf, DEVICE_ID_WORDS);

    // 验证写入的数据
    uint16_t verify[DEVICE_ID_WORDS];
    STMFLASH_Read(DEVICE_ID_FLASH_ADDR, verify, DEVICE_ID_WORDS);

    if (verify[0] != DEVICE_ID_MAGIC || verify[1] != DEVICE_ID_VERSION) {
        printf("Error: Magic number or version mismatch.\n");
        return;
    }

    if (verify[2] != id_low || verify[3] != id_high) {
        printf("Error: Device ID mismatch.\n");
        return;
    }

    if (verify[4] != DeviceID_Checksum(verify[2], verify[3])) {
        printf("Error: Checksum mismatch.\n");
        return;
    }

    printf("Device ID written successfully!\n");
}

// ============================ 用户 ID 读取 ============================
uint8_t DeviceID_Read(uint32_t *device_id)
{
    uint16_t buf[DEVICE_ID_WORDS];

    // 检查 device_id 是否有效
    if (device_id == NULL) {
        return 0;  // 无效的指针
    }

    // 从 Flash 中读取数据
    STMFLASH_Read(DEVICE_ID_FLASH_ADDR, buf, DEVICE_ID_WORDS);

    // 验证数据有效性
    if (buf[0] != DEVICE_ID_MAGIC || buf[1] != DEVICE_ID_VERSION) {
        printf("Error: Magic number or version mismatch.\n");
        return 0;  // 数据无效
    }

    if (buf[4] != DeviceID_Checksum(buf[2], buf[3])) {
        printf("Error: Checksum mismatch.\n");
        return 0;  // 校验和不匹配，数据无效
    }

    // 合并低 16 位和高 16 位
    *device_id = ((uint32_t)buf[3] << 16) | buf[2];

    return 1;  // 成功读取设备 ID
}
