import json
while True:
    task_splits = 'a'
    try:
        for i in range(5):
            try:
                task_splits = json.loads(1)
            except Exception as e:
                if i == 2:
                    raise Exception('Split Faild ' + str(e))
            print(i)
    except Exception as e:
        print(e)