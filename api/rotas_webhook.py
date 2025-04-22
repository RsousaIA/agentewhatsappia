import sys
import os
from flask import Blueprint, request, jsonify
import json
import logging
from datetime import datetime

# Adicionando o diretório raiz ao path para importar módulos
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from database.firebase_db import get_firestore_db
from src.utils.logger import setup_logger
from src.agent.collector_agent import CollectorAgent

# ... existing code ...