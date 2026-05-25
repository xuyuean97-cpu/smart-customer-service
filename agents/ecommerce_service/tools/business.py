"""
业务办理工具模块
"""
from langchain_core.tools import tool
from pydantic import BaseModel,Field
from langchain_core.runnables import RunnableConfig
from common.logging import get_logger
import asyncio

# 获取业务办理工具专用日志记录器
logger = get_logger("agents.tools.business")


class WhellchairRentalRequest(BaseModel):
    name: str = Field(description="预约人姓名")
    id_number: str = Field(description="用户身份证号码,18位数字")
    phone_number: str = Field(description="用户联系方式,11位手机号")
    order_number: str = Field(description="订单号")
    service_date: str = Field(description="服务日期 格式为YYYY-MM-DD HH:MM:SS")


@tool(return_direct=True,args_schema=WhellchairRentalRequest)
async def wheelchair_rental(name: str
                                 , id_number: str
                                 , phone_number: str
                                 , order_number: str
                                 , service_date: str
                                 ,config: RunnableConfig
) -> str:
    """
    售后服务申请工具

    Args:
        request: 售后服务相关请求
    """
    await asyncio.sleep(1)
    logger.info("进入售后服务调用: ")
    logger.info(f"收集到的参数 - 姓名: {name}, 身份证: {id_number}, 电话: {phone_number}, 订单号: {order_number}, 服务日期: {service_date}")

    # 返回表单结构的JSON字符串
    import json

    # 构建表单字段，如果参数有值则添加预填值
    fields = []
    prefilled_fields = []  # 记录预填的字段

    # 姓名字段
    name_field = {
        "id": "cjr",
        "type": "text",
        "label": "预约人姓名",
        "placeholder": "请输入预约人姓名",
        "required": True
    }
    if name and name.strip():  # 如果姓名已收集到
        name_field["value"] = name.strip()
        prefilled_fields.append(f"姓名: {name.strip()}")
    fields.append(name_field)

    # 身份证号码字段
    id_field = {
        "id": "id_number",
        "type": "text",
        "label": "身份证号码",
        "placeholder": "请输入18位身份证号码",
        "required": True,
        "validation": {
            "pattern": "^[0-9]{18}$",
            "error_message": "请输入有效的18位身份证号码"
        }
    }
    if id_number and id_number.strip():  # 如果身份证号已收集到
        id_field["value"] = id_number.strip()
        prefilled_fields.append(f"身份证: {id_number.strip()}")
    fields.append(id_field)

    # 联系电话字段
    phone_field = {
        "id": "cjrdh",
        "type": "tel",
        "label": "联系电话",
        "placeholder": "请输入11位手机号",
        "required": True,
        "validation": {
            "pattern": "^1[3-9][0-9]{9}$",
            "error_message": "请输入有效的11位手机号码"
        }
    }
    if phone_number and phone_number.strip():  # 如果电话号码已收集到
        phone_field["value"] = phone_number.strip()
        prefilled_fields.append(f"电话: {phone_number.strip()}")
    fields.append(phone_field)

    # 服务日期字段
    time_field = {
        "id": "rq",
        "type": "datetime-local",
        "label": "服务日期",
        "placeholder": "请选择服务日期",
        "required": True
    }
    if service_date and service_date.strip():
        time_field["value"] = service_date.strip()
        prefilled_fields.append(f"服务日期: {service_date.strip()}")
    fields.append(time_field)

    # 订单号字段
    order_number_field = {
        "id": "hbxx",
        "type": "text",
        "label": "订单号",
        "placeholder": "请输入订单号",
        "required": True
    }
    if order_number and order_number.strip():
        order_number_field["value"] = order_number.strip()
        prefilled_fields.append(f"订单号: {order_number.strip()}")
    fields.append(order_number_field)

    form_data = {
        "type": "form",
        "title": "售后服务申请",
        "description": "请填写以下信息完成售后服务申请",
        "fields": fields,
        "buttons": [
            {
                "id": "submit",
                "label": "提交申请",
                "type": "submit"
            },
            {
                "id": "cancel",
                "label": "取消",
                "type": "cancel"
            }
        ],
        "action": "/api/v1/business/wheelchair-rental",
        "info": {
            "service_description": "售后服务申请可在线提交退换货、维修等请求，无需拨打客服电话，方便快捷。"
        }
    }

    # 记录预填字段信息
    if prefilled_fields:
        logger.info(f"表单预填字段: {', '.join(prefilled_fields)}")
    else:
        logger.info("无预填字段，返回空白表单")

    return json.dumps(form_data, ensure_ascii=False)

@tool(return_direct=True)
async def test(name: str):
    """这是一个占位工具，暂时不执行任何操作。"""
    print("test",name)
