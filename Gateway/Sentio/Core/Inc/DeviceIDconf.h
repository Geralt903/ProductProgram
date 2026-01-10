#ifndef SENTIO_DEVICEIDCONF_H
#define SENTIO_DEVICEIDCONF_H

#include "main.h"

// ============================ 用户 ID 配置结构体 ============================
typedef struct {
    uint32_t userID;  // 用户 ID，使用 32 位整数
} UserIDConfig, *pUserIDConfig;

// ============================ 用户 ID 配置相关变量 ============================
extern UserIDConfig g_UserIDConfig;

// ============================ 用户 ID 配置函数声明 ============================
void DeviceID_Write(uint32_t device_id);    // 写入设备 ID 到 Flash
uint8_t DeviceID_Read(uint32_t *device_id); // 从 Flash 读取设备 ID

#endif // SENTIO_DEVICEIDCONF_H
