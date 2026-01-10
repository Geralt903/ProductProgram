#include "DeviceIDconf.h"
#include "stmflash.h"

#define DEVICE_ID_FLASH_ADDR FLASH_SAVE_ADDR
#define DEVICE_ID_MAGIC 0xABCDu
#define DEVICE_ID_VERSION 1u

typedef struct {
    uint16_t magic;
    uint16_t version;
    uint16_t id_low;
    uint16_t id_high;
    uint16_t checksum;
} DeviceIDFlashData;

#define DEVICE_ID_WORDS (sizeof(DeviceIDFlashData) / sizeof(uint16_t))

UserIDConfig g_UserIDConfig = {0};

static uint16_t DeviceID_Checksum(const DeviceIDFlashData *data)
{
    return (uint16_t)(data->magic ^ data->version ^ data->id_low ^ data->id_high);
}

static void DeviceID_Pack(DeviceIDFlashData *data, uint32_t device_id)
{
    data->magic = DEVICE_ID_MAGIC;
    data->version = DEVICE_ID_VERSION;
    data->id_low = (uint16_t)(device_id & 0xFFFFu);
    data->id_high = (uint16_t)((device_id >> 16) & 0xFFFFu);
    data->checksum = DeviceID_Checksum(data);
}

static uint8_t DeviceID_Unpack(const DeviceIDFlashData *data, uint32_t *device_id)
{
    if (data->magic != DEVICE_ID_MAGIC || data->version != DEVICE_ID_VERSION) {
        return 0;
    }

    if (data->checksum != DeviceID_Checksum(data)) {
        return 0;
    }

    *device_id = ((uint32_t)data->id_high << 16) | data->id_low;
    return 1;
}

void DeviceID_Write(uint32_t device_id)
{
    DeviceIDFlashData data;

    DeviceID_Pack(&data, device_id);
    STMFLASH_Write(DEVICE_ID_FLASH_ADDR, (uint16_t *)&data, DEVICE_ID_WORDS);

    g_UserIDConfig.userID = device_id;
}

uint8_t DeviceID_Read(uint32_t *device_id)
{
    DeviceIDFlashData data;

    if (device_id == NULL) {
        return 0;
    }

    STMFLASH_Read(DEVICE_ID_FLASH_ADDR, (uint16_t *)&data, DEVICE_ID_WORDS);

    if (!DeviceID_Unpack(&data, device_id)) {
        return 0;
    }

    g_UserIDConfig.userID = *device_id;
    return 1;
}
