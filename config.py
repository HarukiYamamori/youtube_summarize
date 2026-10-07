import os
import tomllib
from dataclasses import dataclass
from logging import getLogger, basicConfig, INFO

basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

CONFIG_PATH = os.getenv('CONFIG_PATH', 'config.toml')

DEFAULT_MODEL = "gemini-3-flash-preview"
# モデルが混雑（503など）・タイムアウトのときに使うモデル。空文字ならフォールバックしない
DEFAULT_FALLBACK_MODEL = "gemini-flash-latest"
DEFAULT_NEW_VIDEO_HOURS = 24
DEFAULT_MAX_CHECK_VIDEOS = 15


@dataclass
class Target:
    url: str
    recipients: list[str]


@dataclass
class Group:
    """複数のURLの要約を1つのダイジェストにまとめて、1通のメールで送る"""
    name: str
    urls: list[str]
    recipients: list[str]
    focus: str = ""


@dataclass
class Config:
    model: str
    fallback_model: str
    new_video_hours: int
    max_check_videos: int
    targets: list[Target]
    groups: list[Group]


def _split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def load_config(path=CONFIG_PATH):
    """設定ファイル（TOML）を読み込む。ファイルが無い場合は環境変数から読み込む"""
    if os.path.exists(path):
        logger.info(f"設定ファイルを読み込みます: {path}")
        with open(path, 'rb') as f:
            data = tomllib.load(f)

        default_recipients = data.get('recipients', [])
        targets = [
            Target(url=t['url'], recipients=t.get('recipients', default_recipients))
            for t in data.get('targets', [])
        ]
        groups = [
            Group(
                name=g.get('name', ''),
                urls=g.get('urls', []),
                recipients=g.get('recipients', default_recipients),
                focus=g.get('focus', ''),
            )
            for g in data.get('groups', [])
        ]
    else:
        logger.info(f"設定ファイルが無いため、環境変数から読み込みます: {path}")
        data = {}
        recipients = _split_csv(os.getenv('EMAIL_ADDRESSES', ''))
        targets = [Target(url=url, recipients=recipients) for url in _split_csv(os.getenv('CHANNEL_URLS', ''))]
        groups = []

    if not targets and not groups:
        raise ValueError("対象のURLが設定されていません（config.tomlのtargets・groups、またはCHANNEL_URLS環境変数）")
    for target in targets:
        if not target.recipients:
            raise ValueError(f"送信先が設定されていません: {target.url}（config.tomlのrecipients、またはEMAIL_ADDRESSES環境変数）")
    for group in groups:
        if not group.name:
            raise ValueError(f"groupsにnameが設定されていません: {group.urls}")
        if not group.urls:
            raise ValueError(f"groupsにurlsが設定されていません: {group.name}")
        if not group.recipients:
            raise ValueError(f"送信先が設定されていません: {group.name}（config.tomlのrecipients）")

    return Config(
        model=data.get('model', DEFAULT_MODEL),
        fallback_model=data.get('fallback_model', DEFAULT_FALLBACK_MODEL),
        new_video_hours=data.get('new_video_hours', DEFAULT_NEW_VIDEO_HOURS),
        max_check_videos=data.get('max_check_videos', DEFAULT_MAX_CHECK_VIDEOS),
        targets=targets,
        groups=groups,
    )
