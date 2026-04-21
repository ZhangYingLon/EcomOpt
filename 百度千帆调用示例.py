# 请安装 OpenAI SDK : pip install openai
# apiKey 获取地址： https://console.bce.baidu.com/qianfan/ais/console/apiKey
# 支持的模型列表： https://cloud.baidu.com/doc/qianfan-docs/s/7m95lyy43

# from openai import OpenAI
# client = OpenAI(
#     base_url='https://qianfan.baidubce.com/v2',
#     + ='密钥'
# )
# response = client.chat.completions.create(
#     model="ernie-4.5-turbo-128k",
#     messages=[],
#     temperature=0.8,
#     top_p=0.8,
#     extra_body={
#         "penalty_score":1,
#         "stop":[],
#         "web_search":{
#     "enable": false,
#     "enable_trace": false
# }
#     }
# )
# print(response)