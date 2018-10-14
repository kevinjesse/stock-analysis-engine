"""
Extract an Yahoo dataset from Redis (S3 support coming soon) and
load it into a ``pandas.DataFrame``

Supported environment variables:

::

    # verbose logging in this module
    export DEBUG_EXTRACT=1

    # verbose logging for just Redis operations in this module
    export DEBUG_REDIS_EXTRACT=1

    # verbose logging for just S3 operations in this module
    export DEBUG_S3_EXTRACT=1

"""

import copy
import pandas as pd
import analysis_engine.extract_utils as extract_utils
import analysis_engine.dataset_scrub_utils as scrub_utils
import analysis_engine.get_data_from_redis_key as redis_get
from spylunking.log.setup_logging import build_colorized_logger
from analysis_engine.consts import SUCCESS
from analysis_engine.consts import ERR
from analysis_engine.consts import NOT_RUN
from analysis_engine.consts import get_status
from analysis_engine.yahoo.consts import DATAFEED_PRICING_YAHOO
from analysis_engine.yahoo.consts import DATAFEED_OPTIONS_YAHOO
from analysis_engine.yahoo.consts import DATAFEED_NEWS_YAHOO
from analysis_engine.yahoo.consts import get_datafeed_str_yahoo

log = build_colorized_logger(
    name=__name__)


def extract_pricing_dataset(
        work_dict,
        scrub_mode='sort-by-date'):
    """extract_pricing_dataset

    Fetch the Yahoo pricing data for a ticker and
    return it as a pandas Dataframe

    :param work_dict: dictionary of args
    :param scrub_mode: type of scrubbing handler to run
    """
    label = work_dict.get('label', 'extract')
    df_type = DATAFEED_PRICING_YAHOO
    df_str = get_datafeed_str_yahoo(df_type=df_type)
    req = copy.deepcopy(work_dict)

    if 'redis_key' not in work_dict:
        # see if it's get dataset dictionary
        if 'pricing' in req:
            req['redis_key'] = req['pricing']
            req['s3_key'] = req['pricing']
    # end of support for the get dataset dictionary

    log.info(
        '{} - {} - start'.format(
            label,
            df_str))

    return extract_utils.perform_extract(
        df_type=df_type,
        df_str=df_str,
        work_dict=req,
        scrub_mode=scrub_mode)
# end of extract_pricing_dataset


def extract_yahoo_news_dataset(
        work_dict,
        scrub_mode='sort-by-date'):
    """extract_yahoo_news_dataset

    Fetch the Yahoo news data for a ticker and
    return it as a pandas Dataframe

    :param work_dict: dictionary of args
    :param scrub_mode: type of scrubbing handler to run
    """
    label = work_dict.get('label', 'extract')
    df_type = DATAFEED_NEWS_YAHOO
    df_str = get_datafeed_str_yahoo(df_type=df_type)
    req = copy.deepcopy(work_dict)

    if 'redis_key' not in work_dict:
        # see if it's get dataset dictionary
        if 'news' in work_dict:
            req['redis_key'] = req['news']
            req['s3_key'] = req['news']
    # end of support for the get dataset dictionary

    log.info(
        '{} - {} - start'.format(
            label,
            df_str))

    return extract_utils.perform_extract(
        df_type=df_type,
        df_str=df_str,
        work_dict=req,
        scrub_mode=scrub_mode)
# end of extract_yahoo_news_dataset


def extract_option_calls_dataset(
        work_dict,
        scrub_mode='sort-by-date'):
    """extract_option_calls_dataset

    Fetch the Yahoo options calls for a ticker and
    return it as a ``pandas.Dataframe``

    :param work_dict: dictionary of args
    :param scrub_mode: type of scrubbing handler to run
    """
    label = '{}-calls'.format(work_dict.get('label', 'extract'))
    ds_id = work_dict.get('ticker')
    df_type = DATAFEED_OPTIONS_YAHOO
    df_str = get_datafeed_str_yahoo(df_type=df_type)
    redis_key = work_dict.get(
        'redis_key',
        work_dict.get('options', 'missing-redis-key'))
    s3_key = work_dict.get(
        's3_key',
        work_dict.get('options', 'missing-s3-key'))
    redis_host = work_dict['redis_host'],
    redis_port = work_dict['redis_port'],
    redis_db = work_dict['redis_db'],

    log.info(
        '{} - {} - start - redis_key={} s3_key={}'.format(
            label,
            df_str,
            redis_key,
            s3_key))

    exp_date_str = None
    calls_df = None
    status = NOT_RUN
    try:
        redis_rec = redis_get.get_data_from_redis_key(
            label=label,
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=work_dict.get('password', None),
            key=redis_key)

        status = redis_rec['status']
        log.info(
            '{} - {} redis get data key={} status={}'.format(
                label,
                df_str,
                redis_key,
                get_status(status=status)))

        if status == SUCCESS:
            print(redis_rec['rec']['data'])
            exp_date_str = redis_rec['rec']['data']['exp_date']
            calls_json = redis_rec['rec']['data']['calls']
            log.info(
                '{} - {} redis convert calls to df'.format(
                    label,
                    df_str))
            calls_df = pd.read_json(
                calls_json,
                orient='records')
            log.info(
                '{} - {} redis_key={} calls={} exp_date={}'.format(
                    label,
                    df_str,
                    redis_key,
                    len(calls_df.index),
                    exp_date_str))
        else:
            log.info(
                '{} - {} did not find valid redis option calls '
                'in redis_key={} status={}'.format(
                    label,
                    df_str,
                    redis_key,
                    get_status(status=status)))

    except Exception as e:
        status = ERR
        log.error(
            '{} - {} - ds_id={} failed getting option calls from '
            'redis={}:{}@{} key={} ex={}'.format(
                label,
                df_str,
                ds_id,
                redis_host,
                redis_port,
                redis_db,
                redis_key,
                e))
        return status, None
    # end of try/ex extract from redis

    log.info(
        '{} - {} ds_id={} extract scrub={}'.format(
            label,
            df_str,
            ds_id,
            scrub_mode))

    scrubbed_df = scrub_utils.extract_scrub_dataset(
        label=label,
        scrub_mode=scrub_mode,
        datafeed_type=df_type,
        msg_format='df={} date_str={}',
        ds_id=ds_id,
        df=calls_df)

    status = SUCCESS

    return status, scrubbed_df
# end of extract_option_calls_dataset


def extract_option_puts_dataset(
        work_dict,
        scrub_mode='sort-by-date'):
    """extract_option_puts_dataset

    Fetch the Yahoo options puts for a ticker and
    return it as a ``pandas.Dataframe``

    :param work_dict: dictionary of args
    :param scrub_mode: type of scrubbing handler to run
    """
    label = '{}-puts'.format(work_dict.get('label', 'extract'))
    ds_id = work_dict.get('ticker')
    df_type = DATAFEED_OPTIONS_YAHOO
    df_str = get_datafeed_str_yahoo(df_type=df_type)
    redis_key = work_dict.get(
        'redis_key',
        work_dict.get('options', 'missing-redis-key'))
    s3_key = work_dict.get(
        's3_key',
        work_dict.get('options', 'missing-s3-key'))
    redis_host = work_dict['redis_host'],
    redis_port = work_dict['redis_port'],
    redis_db = work_dict['redis_db'],

    log.info(
        '{} - {} - start - redis_key={} s3_key={}'.format(
            label,
            df_str,
            redis_key,
            s3_key))

    exp_date_str = None
    puts_df = None
    status = NOT_RUN
    try:
        redis_rec = redis_get.get_data_from_redis_key(
            label=label,
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=work_dict.get('password', None),
            key=redis_key)

        status = redis_rec['status']
        log.info(
            '{} - {} redis get data key={} status={}'.format(
                label,
                df_str,
                redis_key,
                get_status(status=status)))

        if status == SUCCESS:
            print(redis_rec['rec']['data'])
            exp_date_str = redis_rec['rec']['data']['exp_date']
            puts_json = redis_rec['rec']['data']['puts']
            log.info(
                '{} - {} redis convert puts to df'.format(
                    label,
                    df_str))
            puts_df = pd.read_json(
                puts_json,
                orient='records')
            log.info(
                '{} - {} redis_key={} puts={} exp_date={}'.format(
                    label,
                    df_str,
                    redis_key,
                    len(puts_df.index),
                    exp_date_str))
        else:
            log.info(
                '{} - {} did not find valid redis option puts '
                'in redis_key={} status={}'.format(
                    label,
                    df_str,
                    redis_key,
                    get_status(status=status)))

    except Exception as e:
        status = ERR
        log.error(
            '{} - {} - ds_id={} failed getting option puts from '
            'redis={}:{}@{} key={} ex={}'.format(
                label,
                df_str,
                ds_id,
                redis_host,
                redis_port,
                redis_db,
                redis_key,
                e))
        return status, None
    # end of try/ex extract from redis

    log.info(
        '{} - {} ds_id={} extract scrub={}'.format(
            label,
            df_str,
            ds_id,
            scrub_mode))

    scrubbed_df = scrub_utils.extract_scrub_dataset(
        label=label,
        scrub_mode=scrub_mode,
        datafeed_type=df_type,
        msg_format='df={} date_str={}',
        ds_id=ds_id,
        df=puts_df)

    status = SUCCESS

    return status, scrubbed_df
# end of extract_option_puts_dataset
