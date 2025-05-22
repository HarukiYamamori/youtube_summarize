import shutil
import os
from logging import basicConfig, INFO, getLogger

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)


def delete_all_files(directory="data"):
    """ 指定ディレクトリ内のすべてのファイルを削除する """
    if not os.path.exists(directory):
        print(f"ディレクトリ '{directory}' が存在しません。")
        return

    # ディレクトリ内のすべてのファイルを削除
    shutil.rmtree(directory)
    os.makedirs(directory)  # 空のディレクトリを再作成

    logger.info(f"deleted all files in '{directory}'")
