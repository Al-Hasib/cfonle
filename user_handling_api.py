import aiocron
from pydantic import BaseModel
from enum import Enum 
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Query, Form
import uuid


DATA_PATH = "data.csv"
app = FastAPI()

def update_limit_column():
    df = pd.read_csv("user_handling.csv")

    df['daily_used'] = 0  # you can set logic here to compute values
    
    # Save updated data
    df.to_csv("user_handling.csv", index=False)
    print("Limit column updated")

# Schedule this to run every day at midnight (00:00)
@aiocron.crontab('0 0 * * *')  # runs daily at 00:00
async def scheduled_task():
    update_limit_column()


@app.post("/create_user")
async def create_user(name: str, 
                daily_limit:int,
                life_time_limit:int):
    data = pd.read_csv("user_handling.csv")
    new_row_index = len(data)
    random_number = uuid.uuid4()
    data.loc[new_row_index] = [name, str(random_number), daily_limit, 0, life_time_limit, 0, 000000]
    data.to_csv("user_handling.csv", index=False)
    return{
        "status": "User creation successful",
        "user_id": str(random_number),
        "message": "Please provide the user ID through telegram bot to get access."
    }

@app.get("/get_all_users")
async def get_all_users():
    df = pd.read_csv("user_handling.csv")
    df.fillna("null", inplace=True)
    data = df.to_dict(orient="records") 
    return {'data':data}




@app.post("/update_limit")
async def update_limit(Telegram_id:int, daily_limit:int, total_limit:int):
    df = pd.read_csv("user_handling.csv")
    df.loc[df['telegram_id'] == Telegram_id, 'daily_limit'] = daily_limit
    df.loc[df['telegram_id'] == Telegram_id, 'total_limit'] = total_limit
    df.to_csv('user_handling.csv', index=False)
    filter_data = df[df['telegram_id']==Telegram_id]
    if filter_data.empty:
        return {"error": "Id not found"}
    name = str(filter_data['name'].values[0])
    daily_limit = int(filter_data['daily_limit'].values[0])
    total_limit = str(filter_data['total_limit'].values[0])
    Telegram_id = str(filter_data['telegram_id'].values[0])
    # used_today = str(filter_data['used'].values[0])

    return {
        "name":name,
        "Telegram_id":Telegram_id,
        "daily_limit":daily_limit,
        "total_limit": int(total_limit),
    }

# @app.post("/accept_Id")
# def accept_Id(Id: int):
#     df = pd.read_csv("data.csv")
#     df.loc[df['Id'] == Id, 'status'] = 'active'
#     df.to_csv('data.csv', index=False)

#     filter_data = df[df['Id'] == Id]

#     if filter_data.empty:
#         return {"error": "Id not found"}

#     # Convert to native Python types
#     name = str(filter_data['name'].values[0])
#     id_val = int(filter_data['Id'].values[0])
#     status = str(filter_data['status'].values[0])

#     return {
#         "name": name,
#         "Id": id_val,
#         "Status": status
#     }


# @app.post("/reject_Id")
# def reject_Id(Id:int):
#     df = pd.read_csv("data.csv")
#     df.loc[df['Id'] == Id, 'status'] = 'reject'
#     df.to_csv('data.csv', index=False)
#     filter_data = df[df['Id']==Id]
#     if filter_data.empty:
#         return {"error": "Id not found"}
#     name = str(filter_data['name'].values[0])
#     id = int(filter_data['Id'].values[0])
#     status = str(filter_data['status'].values[0])

#     return {
#         "name":name,
#         "Id":id,
#         "Status":status
#     }

# @app.get("/show_pending")
# def show_pending():
#     df = pd.read_csv("data.csv")
#     active_data = df[df['status'] == 'pending']
#     data_dict = active_data.to_dict(orient='records')
#     return{
#         "Pending_data": data_dict
#     }


# class StatusEnum(str, Enum):
#     active = "active"
#     reject = "reject"
#     pending = "pending"
#     others = "others"

# class Status(BaseModel):
#     status: StatusEnum

# @app.post("/update_status_id")
# async def update_status_id(id: int = Query(..., description="The ID to update"), 
#                            status: StatusEnum = Form(..., description="Status to update")):
#     df = pd.read_csv("data.csv")
#     df.loc[df['Id'] == id, 'status'] = status.value
#     df.to_csv('data.csv', index=False)
#     filter_data = df[df['Id']==id]
#     if filter_data.empty:
#         return {"error": "Id not found"}
#     name = str(filter_data['name'].values[0])
#     id = int(filter_data['Id'].values[0])
#     status = str(filter_data['status'].values[0])
#     limit = str(filter_data['limit'].values[0])
#     used_today = str(filter_data['used'].values[0])

#     return {
#         "name":name,
#         "Id":id,
#         "Status":status,
#         "limit": int(limit),
#         "Used today": int(used_today)
#     }




# @app.get("/all_data")
# def get_all():
#     df = pd.read_csv("data.csv")
#     df.fillna("null", inplace=True)
#     data = df.to_dict(orient="records") 

#     return {"data":data}



