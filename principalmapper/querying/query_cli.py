"""Code to implement the CLI interface to the query component of Principal Mapper"""

#  Copyright (c) NCC Group and Erik Steringer 2020. This file is part of Principal Mapper.
#
#      Principal Mapper is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      Principal Mapper is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with Principal Mapper.  If not, see <https://www.gnu.org/licenses/>.

from argparse import ArgumentParser, Namespace
import json
import logging

from principalmapper.graphing import graph_actions
from principalmapper.querying import query_utils, query_actions
from principalmapper.util import botocore_tools


logger = logging.getLogger(__name__)


def provide_arguments(parser: ArgumentParser):
    """Given a parser object (which should be a subparser), add arguments to provide a CLI interface to the
    query component of Principal Mapper.
    """
    parser.add_argument(
        '-s',
        '--skip-admin',
        action='store_true',
        help='Ignores "admin" level principals when querying about multiple principals in an account'
    )
    parser.add_argument(
        '-u',
        '--include-unauthorized',
        action='store_true',
        help='Includes output to say if a given principal is not able to call an action.'
    )
    query_rpolicy_args = parser.add_mutually_exclusive_group()
    query_rpolicy_args.add_argument(
        '--grab-resource-policy',
        action='store_true',
        help='Retrieves the resource policy for resource in the query. Handles S3, IAM, SNS, SQS, and KMS. Requires an '
             'active session from botocore (cannot use --account param).'
    )
    query_rpolicy_args.add_argument(
        '--resource-policy-text',
        help='The full text of a resource policy to consider during authorization evaluation.'
    )
    parser.add_argument(
        '--resource-owner',
        help='The account ID of the owner of the resource. Required for S3 objects (which do not have it in the ARN).'
    )
    parser.add_argument(
        'query',
        help='The query to execute.'
    )


def process_arguments(parsed_args: Namespace):
    """Given a namespace object generated from parsing args, perform the appropriate tasks. Returns an int
    matching expectations set by /usr/include/sysexits.h for command-line utilities."""

    if parsed_args.account is None:
        session = botocore_tools.get_session(parsed_args.profile)
    else:
        session = None

    graph = graph_actions.get_existing_graph(session, parsed_args.account)
    logger.debug('Querying against graph {}'.format(graph.metadata['account_id']))

    if parsed_args.grab_resource_policy:
        if session is None:
            raise ValueError('Resource policy retrieval requires an active session (missing --profile argument?)')
        resource_policy = query_utils.pull_cached_resource_policy_by_arn(graph.policies, arn=None,
                                                                         query=parsed_args.query)
    elif parsed_args.resource_policy_text:
        resource_policy = json.loads(parsed_args.resource_policy_text)
    else:
        resource_policy = None

    resource_owner = parsed_args.resource_owner

    query_actions.query_response(
        graph, parsed_args.query, parsed_args.skip_admin, resource_policy, resource_owner,
        parsed_args.include_unauthorized
    )

    return 0
