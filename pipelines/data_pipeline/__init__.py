from argparse import ArgumentParser
from pipelines.core.constant import environments, spaces
from pipelines.core.util.configuration_util import SubparserBuilder


@SubparserBuilder
def build_subparsers(subparsers) -> list[ArgumentParser]:
    """
    Build subparsers for the tasks in this module

    :param subparsers: A subparsers object from `argparse.ArgumentParser.add_subparsers()`
    :return: List of ArgumentParser
    """

    parsers: list[ArgumentParser] = []
    parser: ArgumentParser

    task = 'pipelines.data_pipeline.raw.stream_finnhub_to_kafka'
    parser = subparsers.add_parser(task)
    parser.set_defaults(command=task)
    parser.add_argument('-b', '--bucket', help='S3 bucket')
    parser.add_argument('-e', '--env', choices=environments, required=True, help='Environment')
    parser.add_argument('-s', '--space', choices=spaces, required=True, help='Space')
    parser.add_argument('--config', help='Configuration file')
    parsers.append(parser)

    task = 'pipelines.data_pipeline.bronze.kafka_bronze_ingestion'
    parser = subparsers.add_parser(task)
    parser.set_defaults(command=task)
    parser.add_argument('-b', '--bucket', help='S3 bucket')
    parser.add_argument('-e', '--env', choices=environments, required=True, help='Environment')
    parser.add_argument('-s', '--space', choices=spaces, required=True, help='Space')
    parser.add_argument('--config', help='Configuration file')
    parsers.append(parser)

    task = 'pipelines.data_pipeline.bronze.transform_data_task'
    parser = subparsers.add_parser(task)
    parser.set_defaults(command=task)
    parser.add_argument('-b', '--bucket', help='S3 bucket')
    parser.add_argument('-e', '--env', choices=environments, required=True, help='Environment')
    parser.add_argument('-s', '--space', choices=spaces, required=True, help='Space')
    parser.add_argument('--config', help='Configuration file')
    parsers.append(parser)

    task = 'pipelines.data_pipeline.silver.clean_data_task'
    parser = subparsers.add_parser(task)
    parser.set_defaults(command=task)
    parser.add_argument('-b', '--bucket', help='S3 bucket')
    parser.add_argument('-e', '--env', choices=environments, required=True, help='Environment')
    parser.add_argument('-s', '--space', choices=spaces, required=True, help='Space')
    parser.add_argument('--config', help='Configuration file')
    parsers.append(parser)

    task = 'pipelines.data_pipeline.gold.ohlcv_data_task'
    parser = subparsers.add_parser(task)
    parser.set_defaults(command=task)
    parser.add_argument('-b', '--bucket', help='S3 bucket')
    parser.add_argument('-e', '--env', choices=environments, required=True, help='Environment')
    parser.add_argument('-s', '--space', choices=spaces, required=True, help='Space')
    parser.add_argument('--config', help='Configuration file')
    parsers.append(parser)

    return parsers
