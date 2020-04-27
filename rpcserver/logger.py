import logging.config

LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
        'detail': {
            'format': '%(asctime)s %(filename)s[%(lineno)d]:%(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple'
        }
    },
    'loggers':{
        'rpc.access': {
            'handlers': ['console'],
            'level': 'DEBUG',
            "formatter": 'detail'
        },
    }
}

logging.config.dictConfig(LOGGING)
logger = logging.getLogger('rpc.access')