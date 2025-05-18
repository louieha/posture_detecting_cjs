"""
애플리케이션 로깅 설정 관리
"""
import logging
import logging.config
import os
from pathlib import Path
from typing import Optional

import toml


def setup_logging(config_path: Optional[str] = None) -> None:
    """
    로깅 시스템 설정을 로드하고 초기화합니다.
    
    Args:
        config_path: 로깅 설정 파일 경로. 없으면 기본 설정 사용
    """
    # 기본 설정 경로
    if config_path is None:
        # 프로젝트 루트의 config 디렉토리
        base_dir = Path(__file__).parent.parent.parent
        config_path = os.path.join(base_dir, "config", "logging.toml")
    
    # 설정 파일이 존재하는 경우 로드
    if os.path.exists(config_path):
        try:
            config = toml.load(config_path)
            logging.config.dictConfig(config["logging"])
            logging.info(f"로깅 설정 로드됨: {config_path}")
            return
        except Exception as e:
            print(f"로깅 설정 로드 실패: {e}")
    
    # 기본 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("기본 로깅 설정 적용됨")


def get_logger(name: str) -> logging.Logger:
    """
    지정된 이름으로 로거 인스턴스를 반환합니다.
    
    Args:
        name: 로거 이름
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    return logging.getLogger(name) 