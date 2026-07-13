#!/usr/bin/env python3
"""DryRunSecurity API helper for finding remediation.

Reads the API key from the DRYRUN_API_KEY environment variable.
Uses only Python 3 standard library — no pip dependencies required.

Usage:
    python3 dryrun_api.py <command> [flags]

Commands:
    list-accounts            List accounts accessible by the API key
    list-repos               List repositories for an account
    list-scans               List PR scans for a repository
    get-scan                 Get detailed PR scan results with findings
    list-deepscans           List deepscans for a repo (auto-picks latest)
    get-deepscan-results     Get deepscan code findings
    get-sca-results          Get SCA findings for a deepscan

All list commands support --page (default 1) and --per-page (default 50, max 100).
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

BASE_URL = "https://simple-api.dryrun.security"


def get_api_key():
    key = os.environ.get("DRYRUN_API_KEY")
    if not key:
        print(json.dumps({
            "error": "DRYRUN_API_KEY environment variable is not set. "
                     "Set it with: export DRYRUN_API_KEY=your-key-here"
        }, indent=2))
        sys.exit(1)
    return key


def make_request(path, params=None):
    url = BASE_URL + path
    if params:
        query = urllib.parse.urlencode(params)
        url = url + "?" + query

    key = get_api_key()
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + key,
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        error_msg = {
            "error": "HTTP {}".format(e.code),
            "status_code": e.code,
            "url": url,
        }
        if e.code == 404:
            error_msg["message"] = "Not found. Check that the account_id, repo_id, scan_id, or deepscan_id is correct."
        try:
            error_msg["response_body"] = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            error_msg["response_body"] = body
        print(json.dumps(error_msg, indent=2))
        sys.exit(1)
    except urllib.error.URLError as e:
        print(json.dumps({
            "error": "Connection error",
            "message": str(e.reason),
            "url": url,
        }, indent=2))
        sys.exit(1)


def build_pagination(args):
    params = {}
    if args.page is not None:
        params["page"] = args.page
    if args.per_page is not None:
        params["per_page"] = args.per_page
    return params


def cmd_list_accounts(args):
    result = make_request("/v1/accounts")
    print(json.dumps(result, indent=2))


def cmd_list_repos(args):
    params = build_pagination(args)
    path = "/v1/accounts/{}/repositories".format(args.account_id)
    result = make_request(path, params or None)
    print(json.dumps(result, indent=2))


def cmd_list_scans(args):
    params = build_pagination(args)
    if args.severity:
        params["severity"] = args.severity
    if args.pr_number is not None:
        params["pr_number"] = args.pr_number
    if args.date_from:
        params["date_from"] = args.date_from
    if args.date_to:
        params["date_to"] = args.date_to
    path = "/v1/accounts/{}/repositories/{}/scans".format(args.account_id, args.repo_id)
    result = make_request(path, params or None)
    print(json.dumps(result, indent=2))


def cmd_get_scan(args):
    params = {}
    if args.findings_result:
        params["findings_result"] = args.findings_result
    if args.page is not None:
        params["page"] = args.page
    if args.per_page is not None:
        params["per_page"] = args.per_page
    path = "/v1/accounts/{}/repositories/{}/scans/{}".format(
        args.account_id, args.repo_id, args.scan_id
    )
    result = make_request(path, params or None)
    print(json.dumps(result, indent=2))


def cmd_list_deepscans(args):
    path = "/v1/accounts/{}/repositories/{}/deepscans".format(
        args.account_id, args.repo_id
    )
    result = make_request(path)
    data = result.get("data", [])
    if not data:
        print(json.dumps({
            "error": "No deepscans found for this repository.",
            "account_id": args.account_id,
            "repo_id": args.repo_id,
        }, indent=2))
        sys.exit(1)

    latest = max(data, key=lambda d: d.get("created_at", ""))
    print(json.dumps({
        "latest_deepscan": {
            "id": latest.get("id"),
            "branch": latest.get("branch"),
            "commit_sha": latest.get("commit_sha"),
            "created_at": latest.get("created_at"),
            "type": latest.get("type"),
        }
    }, indent=2))


def cmd_get_deepscan_results(args):
    params = {}
    if args.severity:
        params["severity"] = args.severity
    if args.page is not None:
        params["page"] = args.page
    if args.per_page is not None:
        params["per_page"] = args.per_page
    path = "/v1/accounts/{}/repositories/{}/deepscans/{}/results".format(
        args.account_id, args.repo_id, args.deepscan_id
    )
    result = make_request(path, params or None)
    print(json.dumps(result, indent=2))


def cmd_get_sca_results(args):
    params = {}
    if args.severity:
        params["severity"] = args.severity
    if args.page is not None:
        params["page"] = args.page
    if args.per_page is not None:
        params["per_page"] = args.per_page
    path = "/v1/accounts/{}/repositories/{}/deepscans/{}/sca_results".format(
        args.account_id, args.repo_id, args.deepscan_id
    )
    result = make_request(path, params or None)
    print(json.dumps(result, indent=2))


def add_pagination_args(parser):
    parser.add_argument("--page", type=int, default=None,
                        help="Page number (default: 1)")
    parser.add_argument("--per-page", type=int, default=None,
                        help="Results per page (default: 50, max: 100)")


def main():
    parser = argparse.ArgumentParser(
        description="DryRunSecurity API helper for finding remediation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="API command")

    subparsers.add_parser("list-accounts", help="List accounts accessible by the API key")

    p_repos = subparsers.add_parser("list-repos", help="List repositories for an account")
    p_repos.add_argument("--account-id", required=True, help="Account ID (UUID)")
    add_pagination_args(p_repos)

    p_scans = subparsers.add_parser("list-scans", help="List PR scans for a repository")
    p_scans.add_argument("--account-id", required=True, help="Account ID (UUID)")
    p_scans.add_argument("--repo-id", required=True, help="Repository ID (UUID)")
    p_scans.add_argument("--severity", default=None,
                         help="Filter by severity (comma-separated: critical,high,medium,low)")
    p_scans.add_argument("--pr-number", type=int, default=None,
                         help="Filter scans by pull request number")
    p_scans.add_argument("--date-from", default=None,
                         help="Filter scans from this date (ISO 8601)")
    p_scans.add_argument("--date-to", default=None,
                         help="Filter scans to this date (ISO 8601)")
    add_pagination_args(p_scans)

    p_scan = subparsers.add_parser("get-scan", help="Get detailed PR scan results with findings")
    p_scan.add_argument("--account-id", required=True, help="Account ID (UUID)")
    p_scan.add_argument("--repo-id", required=True, help="Repository ID (UUID)")
    p_scan.add_argument("--scan-id", required=True, help="Scan ID (UUID)")
    p_scan.add_argument("--findings-result", default=None,
                        help="Filter findings by severity (comma-separated: failing,risky,info)")
    p_scan.add_argument("--page", type=int, default=None, help="Page number (default: 1)")
    p_scan.add_argument("--per-page", type=int, default=None,
                        help="Results per page (default: 50, max: 100)")

    p_deepscans = subparsers.add_parser("list-deepscans",
                                        help="List deepscans for a repo (auto-picks latest)")
    p_deepscans.add_argument("--account-id", required=True, help="Account ID (UUID)")
    p_deepscans.add_argument("--repo-id", required=True, help="Repository ID (UUID)")

    p_ds_results = subparsers.add_parser("get-deepscan-results",
                                         help="Get deepscan code findings")
    p_ds_results.add_argument("--account-id", required=True, help="Account ID (UUID)")
    p_ds_results.add_argument("--repo-id", required=True, help="Repository ID (UUID)")
    p_ds_results.add_argument("--deepscan-id", required=True, help="Deepscan ID (UUID)")
    p_ds_results.add_argument("--severity", default=None,
                              help="Filter by severity (comma-separated: critical,high,medium,low)")
    add_pagination_args(p_ds_results)

    p_sca = subparsers.add_parser("get-sca-results", help="Get SCA findings for a deepscan")
    p_sca.add_argument("--account-id", required=True, help="Account ID (UUID)")
    p_sca.add_argument("--repo-id", required=True, help="Repository ID (UUID)")
    p_sca.add_argument("--deepscan-id", required=True, help="Deepscan ID (UUID)")
    p_sca.add_argument("--severity", default=None,
                       help="Filter by severity (comma-separated: critical,high,medium,low)")
    add_pagination_args(p_sca)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "list-accounts": cmd_list_accounts,
        "list-repos": cmd_list_repos,
        "list-scans": cmd_list_scans,
        "get-scan": cmd_get_scan,
        "list-deepscans": cmd_list_deepscans,
        "get-deepscan-results": cmd_get_deepscan_results,
        "get-sca-results": cmd_get_sca_results,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
