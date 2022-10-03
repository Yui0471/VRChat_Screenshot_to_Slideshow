# -*- coding : utf-8 -*-

import cv2
import glob
import os
import sys
import time
from PIL import Image
import tqdm
import datetime
import ctypes
import subprocess
import pprint

credit = """
【 VRChat Screenshot to Slideshow 】
    Version 0.0.0
    VRChatのスクリーンショットからスライドショーを生成するツール

            製作 : 風庭ゆい
            Special thanks! : ぐー
"""

# CUI上で色を使用する
ENABLE_PROCESSED_OUTPUT = 0x0001
ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
MODE = ENABLE_PROCESSED_OUTPUT + ENABLE_WRAP_AT_EOL_OUTPUT + ENABLE_VIRTUAL_TERMINAL_PROCESSING
 
kernel32 = ctypes.windll.kernel32
handle = kernel32.GetStdHandle(-11)
kernel32.SetConsoleMode(handle, MODE)

RED = "\033[31m"
END = "\033[0m"

# ディレクトリのパスを渡すと中にあるpngのパスをリスト化して返す
def png_path_get(file_path):
    file_list = []
    files = glob.glob(file_path + "\*.png")
    for path in files:
        file_list.append(path)

    print("画像データを", len(file_list), "件取得しました")

    return file_list

# 作成日時を取得しパスと一緒に辞書型に格納する
def birthtime_get(file_list):
    path_birth = {}
    for path in file_list:
        # ctime -> 作成日時 mtime -> 更新日時 : 値が小さい方(過去の時間を参照する)を優先
        if os.path.getmtime(path) <= os.path.getctime(path):
            datatime = os.path.getmtime(path)
        elif os.path.getmtime(path) >= os.path.getctime(path):
            datatime = os.path.getctime(path)

        path_birth[datatime] = path

    print("更新日時の取得に成功しました")
    
    return path_birth

# 作成日時を基に並び替え
def birthtime_sorted(path_birth):
    sorted_list = sorted(path_birth.items())

    print("更新日時でソートが完了しました")

    return sorted_list

# https://daeudaeu.com/pil-aspect/
# 画像のサイズと指定されたサイズを基にアスペクト比を変更しないサイズを出力
def keepAspectResize(path, size):
    # 画像の読み込み
    image = Image.open(path)
    # サイズを幅と高さにアンパック
    width, height = size
    # 矩形の幅と画像の幅の比率を計算
    x_ratio = width / image.width
    # 矩形の高さと画像の高さの比率を計算
    y_ratio = height / image.height
    # 画像の幅と高さ両方に小さい方の比率を掛けてリサイズ後のサイズを計算
    if x_ratio < y_ratio:
        resize_size = (width, round(image.height * x_ratio))
    else:
        resize_size = (round(image.width * y_ratio), height)
    # リサイズ後の画像サイズにリサイズ
    #resized_image = image.resize(resize_size)

    #return resized_image
    return resize_size

# https://qiita.com/iroha71/items/691367b77b52dae8cbaf
# 画像サイズを1920,1080に合わせるために余白を黒塗りする
def expand(img, size):
    height, width, color = img.shape # 画像の縦横サイズを取得
    export_width, export_height = size

    # 縦長画像→幅を拡張する
    if height > width:
        diffsize = export_width - width
        # 元画像を中央ぞろえにしたいので、左右に均等に余白を入れる
        padding_half = int(diffsize / 2)
        padding_img = cv2.copyMakeBorder(img, 0, 0, padding_half, padding_half, cv2.BORDER_CONSTANT, (0, 0, 0))
        #cv2.imwrite('./sample@padding.jpg', padding_img)

    # 横長画像→高さを拡張する
    elif width > height:
        diffsize = export_height - height
        padding_half = int(diffsize / 2)
        padding_img = cv2.copyMakeBorder(img, padding_half, padding_half, 0, 0, cv2.BORDER_CONSTANT, (0, 0, 0))
        #cv2.imwrite('./sample@padding.jpg', padding_img)
    
    return padding_img

# アスペクト比の計算
def aspect_ratio(ox, oy):
    x, y = ox, oy
    while y:
        x, y = y, x % y
    return (ox/x, oy/x)

# ファイル名の生成
def export_filename(size):
    dt_now = datetime.datetime.now()
    return "Export_" + dt_now.strftime("%Y-%m-%d_%H-%M-%S.%f") + ".mp4"

# mp4書き出し
def mp4_generation(sorted_list):
    print("本スクリプトはOpenH264を使用してファイルを生成します :", "\n")

    size = (1920, 1080) # サイズ指定
    fourcc = cv2.VideoWriter_fourcc("H", "2", "6", "4") # フォーマット指定(H264)
    flame_rate = len(sorted_list) / 139 # フレームレート計算, 総枚数と140秒(2分20秒)で割る
    export_file = export_filename(size) 
    save = cv2.VideoWriter(export_file, fourcc, flame_rate, size)

    print("出力サイズ :", size)
    print("出力形式 :", "H264")
    print("書き出しファイル名 :", export_file)
    print("ファイルはカレントディレクトリに生成されます")
    print("データの書き出しを開始します...")

    for path in tqdm.tqdm(sorted_list):
        img_path = path[1]
        img = cv2.imread(img_path)
        
        height, width, color = img.shape
        # 16:9の画像ではない場合(縦画像など)
        if not aspect_ratio(width, height) == (16,9):
            # 画像を縮小したのちに1920,1080に合うように余白を埋める
            img_resize = expand(cv2.resize(img, keepAspectResize(img_path, size)), size)

        else:
            # 1920,1080にリサイズ
            img_resize = cv2.resize(img, size)
        save.write(img_resize)
    
    save.release()

    print("データの書き出しを完了しました")

if __name__ == "__main__":
    print(credit)

    if not os.path.isfile(".\\openh264-1.8.0-win64.dll"):
        print(RED, "[Error!] OpenH264ファイルが見つかりません!", END)
        print("このスクリプトを使用するにはOpenH264 ver1.8.0が必要です")
        subprocess.call("PAUSE", shell=True)

    # 通常動作モード(ドラッグアンドドロップで起動)
    if not len(sys.argv) <= 1:
        print("通常動作モードが選択されました")

        file_path = sys.argv[1]
        print("フォルダパスを取得しました: ", file_path)

        # ディレクトリかどうか判定
        if os.path.isdir(file_path):
            print("処理を開始します")

            mp4_generation(birthtime_sorted(birthtime_get(png_path_get(file_path))))

            print("処理を正常に終了しました")
            time.sleep(1)
        
        else:
            print(RED, "[Error!] フォルダ以外が選択されました！ 処理が続行できません", END)
            print("ドラッグアンドドロップで使用可能なのは[フォルダ]のみです")
            subprocess.call("PAUSE", shell=True)

    # 特殊操作モード(ダブルクリックで起動)
    else:
        print("特殊操作モードが選択されました")

        print("\n1 : 通常動作モード\n2 : 写真選択モード\n3 : デバッグモード\n")

        mode = input("起動したいモードの数字を入力してください : ")

        if mode == "1":
            print("通常動作モードが選択されました")
            file_path = input("処理したいディレクトリをドラッグアンドドロップしてEnterを押してください : ")

            if os.path.isdir(file_path):
                print("処理を開始します")

                mp4_generation(birthtime_sorted(birthtime_get(png_path_get(file_path))))

                print("処理を正常に終了しました")
                time.sleep(1)
            
            else:
                print(RED, "[Error!] フォルダ以外が選択されました！ 処理が続行できません", END)
                print("ドラッグアンドドロップで使用可能なのは[フォルダ]のみです")
                subprocess.call("PAUSE", shell=True)

        elif mode == "2":
            print("写真選択モードが選択されました")

        elif mode == "3":
            print("デバッグモードが選択されました")
            print("[Warning!] このモードは大量のログが生成されます")
            file_path = input("処理したいディレクトリをドラッグアンドドロップしてEnterを押してください : ")

            print("処理を開始します")
            file_list = png_path_get(file_path)
            pprint.pprint(file_list)
            path_birth = birthtime_get(file_list)
            pprint.pprint(path_birth)
            sorted_list = birthtime_sorted(path_birth)
            for tuple in sorted_list:
                print(tuple)
            mp4_generation(sorted_list)
            print("処理を正常に終了しました")
            subprocess.call("PAUSE", shell=True)

        else:
            print(RED, "[Error!] 数字以外が入力されました! 処理を続行できません", END)
            print("最初からやり直してください")
            subprocess.call("PAUSE", shell=True)

    
