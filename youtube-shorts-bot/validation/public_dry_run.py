"""Dispatch and synchronously verify one exact public runtime dry run."""

import hashlib
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PublicDryRunError(RuntimeError):
    pass


def correlation_id(run_id, run_attempt, expected_sha):
    if not str(run_id).isdigit() or not str(run_attempt).isdigit():
        raise PublicDryRunError('E_DRY_PRIVATE_ID')
    if not re.fullmatch(r'[0-9a-f]{40}', str(expected_sha)):
        raise PublicDryRunError('E_DRY_PUBLIC_SHA')
    seed = f'{run_id}:{run_attempt}:{expected_sha}'.encode()
    return 'dr_' + hashlib.sha256(seed).hexdigest()[:24]


def select_correlated_run(runs, before_ids, expected_sha, correlation, jobs_by_run):
    matches = []
    wanted_job = f'dry-run-{correlation}'
    for run in runs:
        run_id = int(run.get('id', 0) or 0)
        if not run_id or run_id in before_ids:
            continue
        if run.get('event') != 'workflow_dispatch':
            continue
        jobs = jobs_by_run.get(run_id, [])
        if not any(job.get('name') == wanted_job for job in jobs):
            continue
        if run.get('head_sha') != expected_sha:
            raise PublicDryRunError(
                f'E_DRY_PUBLIC_SHA expected={expected_sha} actual={run.get("head_sha")}'
            )
        matches.append(run)
    if len(matches) > 1:
        raise PublicDryRunError('E_DRY_PUBLIC_AMBIGUOUS')
    return matches[0] if matches else None


class GitHubApi:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise PublicDryRunError('E_DRY_PUBLIC_REPOSITORY')
        if not token:
            raise PublicDryRunError('E_DRY_PUBLIC_TOKEN')
        self.repository = repository
        self.token = token

    def call(self, endpoint, method='GET', body=None):
        url = f'https://api.github.com/repos/{self.repository}/{endpoint}'
        data = None if body is None else json.dumps(body).encode()
        request = Request(
            url,
            data=data,
            method=method,
            headers={
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
                'Content-Type': 'application/json',
            },
        )
        try:
            with urlopen(request, timeout=45) as response:
                raw = response.read()
                return None if not raw else json.loads(raw)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise PublicDryRunError(f'E_DRY_PUBLIC_API {method} {endpoint}: {exc}') from None


def _runs(api, workflow):
    payload = api.call(
        f'actions/workflows/{workflow}/runs?event=workflow_dispatch&branch=main&per_page=100'
    )
    return list((payload or {}).get('workflow_runs') or [])


def _jobs(api, run_id):
    payload = api.call(f'actions/runs/{run_id}/jobs?per_page=100')
    return list((payload or {}).get('jobs') or [])


def dispatch_and_verify():
    repository = os.environ.get('PUBLIC_REPOSITORY', 'skyfremen/production-runtime')
    workflow = os.environ.get('PUBLIC_DRY_RUN_WORKFLOW', 'dry-run.yml')
    token = os.environ.get('PUBLIC_PRODUCTION_TOKEN', '')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    run_attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '')
    api = GitHubApi(repository, token)

    commit = api.call('commits/main')
    expected_sha = str((commit or {}).get('sha', ''))
    if not re.fullmatch(r'[0-9a-f]{40}', expected_sha):
        raise PublicDryRunError('E_DRY_PUBLIC_SHA')

    correlation = correlation_id(run_id, run_attempt, expected_sha)
    before_ids = {int(item['id']) for item in _runs(api, workflow) if item.get('id')}
    api.call(
        f'actions/workflows/{workflow}/dispatches',
        method='POST',
        body={
            'ref': 'main',
            'inputs': {
                'correlation_id': correlation,
                'expected_sha': expected_sha,
            },
        },
    )
    print(f'Public dry run dispatched correlation={correlation} expected_sha={expected_sha}')

    discovery_deadline = time.monotonic() + 120
    linked = None
    while time.monotonic() < discovery_deadline:
        runs = _runs(api, workflow)
        jobs_by_run = {}
        for run in runs:
            current_id = int(run.get('id', 0) or 0)
            if current_id and current_id not in before_ids:
                jobs_by_run[current_id] = _jobs(api, current_id)
        linked = select_correlated_run(
            runs,
            before_ids=before_ids,
            expected_sha=expected_sha,
            correlation=correlation,
            jobs_by_run=jobs_by_run,
        )
        if linked is not None:
            break
        time.sleep(3)
    if linked is None:
        raise PublicDryRunError('E_DRY_PUBLIC_NO_RUN')

    linked_id = int(linked['id'])
    completion_deadline = time.monotonic() + 600
    while time.monotonic() < completion_deadline:
        current = api.call(f'actions/runs/{linked_id}')
        if current.get('head_sha') != expected_sha:
            raise PublicDryRunError(
                f'E_DRY_PUBLIC_SHA expected={expected_sha} actual={current.get("head_sha")}'
            )
        if current.get('status') == 'completed':
            conclusion = current.get('conclusion')
            if conclusion != 'success':
                raise PublicDryRunError(
                    f'E_DRY_PUBLIC_RESULT run_id={linked_id} conclusion={conclusion}'
                )
            print(
                f'Linked public dry run PASS run_id={linked_id} '
                f'correlation={correlation} sha={expected_sha}'
            )
            return linked_id
        time.sleep(5)

    raise PublicDryRunError(f'E_DRY_PUBLIC_TIMEOUT run_id={linked_id}')


def main():
    try:
        dispatch_and_verify()
    except PublicDryRunError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
