"""Execute model-authored XPath configurations without executing model code.

The child process owns parsing, XPath evaluation and extraction. A successful
runtime result is not a claim of complete or noise-free article extraction.
"""
from __future__ import annotations

import json
import math
import multiprocessing
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import uuid

from lxml import html
from lxml.html import HtmlElement

from .extractor import extract_html


MAX_XPATH_LENGTH = 4096
MAX_EXCLUSIONS = 32
MAX_SOURCE_BYTES = 10 * 1024 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def validate_rule(rule: dict | str) -> dict:
    """Return a copied strict version-1 rule, or raise ValueError."""
    if isinstance(rule, str):
        try:
            rule = json.loads(rule, object_pairs_hook=_unique_object)
        except (ValueError, TypeError) as error:
            raise ValueError(f'Invalid rule JSON: {error}') from error
    if not isinstance(rule, dict):
        raise ValueError('Rule must be a JSON object')
    if set(rule) != {'version', 'container_xpath', 'exclude_xpaths'}:
        raise ValueError('Required keys are exactly version, container_xpath, exclude_xpaths')
    if type(rule['version']) is not int or rule['version'] != 1:
        raise ValueError('version must be integer 1')
    exclusions = rule['exclude_xpaths']
    if not isinstance(exclusions, list) or len(exclusions) > MAX_EXCLUSIONS:
        raise ValueError(f'exclude_xpaths must be a list of at most {MAX_EXCLUSIONS} expressions')
    for expression in [rule['container_xpath'], *exclusions]:
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError('Every XPath must be a nonempty string')
        if len(expression) > MAX_XPATH_LENGTH:
            raise ValueError(f'XPath exceeds {MAX_XPATH_LENGTH} characters')
    return dict(version=1, container_xpath=rule['container_xpath'],
                exclude_xpaths=list(exclusions))


class RuleExecutionError(ValueError):
    def __init__(self, status, message, match_count=None):
        super().__init__(message)
        self.status = status
        self.match_count = match_count


def _elements(context, expression, label):
    try:
        nodes = context.xpath(expression)
    except Exception as error:
        raise RuleExecutionError('invalid_xpath', f'{label}: {error}') from error
    if not isinstance(nodes, list) or any(not isinstance(node, HtmlElement) for node in nodes):
        raise RuleExecutionError('non_element_xpath', f'{label} must select only HTML elements')
    return nodes


def _execute(source, rule):
    if not source.strip():
        raise RuleExecutionError('empty_input', 'HTML input is empty')
    tree = html.document_fromstring(source, parser=html.HTMLParser(no_network=True))
    matches = _elements(tree, rule['container_xpath'], 'container_xpath')
    if len(matches) != 1:
        status = 'rule_no_match' if not matches else 'rule_ambiguous'
        raise RuleExecutionError(status, 'Container must match exactly one element', len(matches))
    selected = matches[0]
    original_path = tree.getroottree().getpath(selected)
    descendants = set(selected.iterdescendants())
    removals = set()
    # Validate all expressions before deleting anything. An outside selection
    # must not disappear merely because an earlier exclusion removed its parent.
    for index, expression in enumerate(rule['exclude_xpaths']):
        nodes = _elements(selected, expression, f'exclude_xpaths[{index}]')
        if any(node not in descendants for node in nodes):
            raise RuleExecutionError('exclusion_outside_container',
                                     f'exclude_xpaths[{index}] selects the container or an outside node', 1)
        removals.update(nodes)
    topmost = [node for node in removals if not any(parent in removals for parent in node.iterancestors())]
    for node in topmost:
        node.drop_tree()  # lxml preserves tail text in the original position.
    # The user XPath can be positional or depend on the very nodes just removed.
    # A private marker maintains identity across serialization and reparsing.
    marker = 'data-webextract-agent-selected'
    for node in tree.iter():
        if isinstance(node.tag, str):
            node.attrib.pop(marker, None)
    token = uuid.uuid4().hex
    selected.set(marker, token)
    result = extract_html(html.tostring(tree, encoding='unicode'),
                          container_xpath=f'//*[@{marker}="{token}"]')
    return dict(status=result.status, match_count=1, error=None,
                selected_xpath=original_path, excluded_count=len(topmost),
                result=result.to_dict())


def _worker(source, rule, output_path):
    try:
        response = _execute(source, rule)
    except RuleExecutionError as error:
        response = dict(status=error.status, match_count=error.match_count,
                        error=str(error), result=None)
    except Exception as error:
        response = dict(status='execution_error', match_count=None,
                        error=f'{type(error).__name__}: {error}', result=None)
    Path(output_path).write_text(json.dumps(response, ensure_ascii=False), encoding='utf-8')


def execute_rule(source: str | bytes, rule: dict | str, *, timeout_seconds: float = 5.0) -> dict:
    """Execute one bounded rule; always return serializable runtime feedback.

    Timeout includes process startup, parsing, every XPath and extraction.
    Process termination limits wall time, not memory consumption; this learning
    executor is not an operating-system sandbox for hostile native libraries.
    Call from an importable module under a main guard on Windows.
    """
    started = time.monotonic()
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError('timeout_seconds must be a positive finite number')
    try:
        validated = validate_rule(rule)
    except ValueError as error:
        return dict(status='invalid_rule', match_count=None, error=str(error), result=None, elapsed_seconds=time.monotonic()-started)
    if not isinstance(source, (str, bytes)):
        raise TypeError('source must be str or bytes')
    if len(source.encode('utf-8') if isinstance(source, str) else source) > MAX_SOURCE_BYTES:
        return dict(status='input_too_large', match_count=None, error=f'HTML exceeds {MAX_SOURCE_BYTES} bytes', result=None, elapsed_seconds=time.monotonic()-started)
    context = multiprocessing.get_context('spawn')
    # A file avoids blocking recv() or a child blocked on a full IPC pipe when
    # the extracted result is large. Completion means the worker has exited.
    with TemporaryDirectory(prefix='webextract-rule-') as temporary:
        output_path = Path(temporary) / 'result.json'
        process = context.Process(target=_worker, args=(source, validated, str(output_path)), daemon=True)
        try:
            process.start()
            remaining = max(0.0, timeout_seconds - (time.monotonic()-started))
            process.join(timeout=remaining)
            if process.is_alive():
                response = dict(status='timeout', match_count=None, error='Rule execution exceeded its wall-time limit', result=None)
            elif process.exitcode != 0 or not output_path.exists():
                response = dict(status='worker_error', match_count=None, error=f'Worker exited without a response (exit {process.exitcode})', result=None)
            else:
                response = json.loads(output_path.read_text(encoding='utf-8'))
        except Exception as error:
            response = dict(status='worker_error', match_count=None, error=f'{type(error).__name__}: {error}', result=None)
        finally:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1.0)
                process.close()
    response['elapsed_seconds'] = time.monotonic()-started
    return response
