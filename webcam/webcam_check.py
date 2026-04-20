import cv2

# 依次遍历 0, 1, 2
for i in [0, 1, 2]:
    cap = cv2.VideoCapture(i)
    # 尝试读取一帧
    ret, frame = cap.read()
    if ret:
        cv2.imshow(f'Testing Camera Index {i}', frame)
        print(f"正在预览索引 {i}，按任意键关闭预览...")
        cv2.waitKey(0) # 按任意键进入下一个
        cv2.destroyAllWindows()
    cap.release()