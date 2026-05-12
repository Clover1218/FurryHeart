import jieba

text = "用户和小红在星巴克喝咖啡"
print(list(jieba.lcut(text, HMM=False)))