import operator
import os
from functools import reduce
from io import BytesIO
from typing import Generator, Dict, List, Any

import allure
import pytest
from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch
from playwright.sync_api import Browser, Error, Page, BrowserContext
from pytest_playwright.pytest_playwright import _build_artifact_test_folder, truncate_file_name
from slugify import slugify


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig: Any) -> Dict:
    launch_options = {}
    maximized_option = pytestconfig.getoption("--start-maximized")
    if maximized_option:
        launch_options.setdefault("args", [])
        launch_options["args"].append('--start-maximized')
    return {
        **browser_type_launch_args,
        **launch_options,
    }


@pytest.fixture
def context(
    browser: Browser,
    browser_context_args: Dict,
    pytestconfig: Any,
    request: pytest.FixtureRequest,
) -> Generator[BrowserContext, None, None]:
    pages: List[Page] = []

    context_args_marker = next(request.node.iter_markers("browser_context_args"), None)
    additional_context_args = context_args_marker.kwargs if context_args_marker else {}
    browser_context_args.update(additional_context_args)

    context = browser.new_context(**browser_context_args)
    context.on("page", lambda page: pages.append(page))

    tracing_option = pytestconfig.getoption("--tracing")
    capture_trace = tracing_option in ["on", "retain-on-failure"]
    if capture_trace:
        context.tracing.start(
            title=slugify(request.node.nodeid),
            screenshots=True,
            snapshots=True,
            sources=True,
        )

    yield context

    # If request.node is missing rep_call, then some error happened during execution
    # that prevented teardown, but should still be counted as a failure
    failed = request.node.rep_call.failed if hasattr(request.node, "rep_call") else True

    if capture_trace:
        retain_trace = tracing_option == "on" or (
            failed and tracing_option == "retain-on-failure"
        )
        if retain_trace:
            trace_path = _build_artifact_test_folder(pytestconfig, request, "trace.zip")
            context.tracing.stop(path=trace_path)
            allure.attach.file(trace_path, 'trace', extension='zip')
        else:
            context.tracing.stop()

    screenshot_option = pytestconfig.getoption("--screenshot")
    capture_screenshot = screenshot_option == "on" or (
        failed and screenshot_option == "only-on-failure"
    )
    if capture_screenshot:
        for index, page in enumerate(pages):
            human_readable_status = "failed" if failed else "finished"
            screenshot_path = _build_artifact_test_folder(
                pytestconfig, request, f"test-{human_readable_status}-{index+1}.png"
            )
            try:
                page.screenshot(
                    timeout=5000,
                    path=screenshot_path,
                    full_page=pytestconfig.getoption("--full-page-screenshot"),
                )
                allure.attach.file(screenshot_path, "screenshot", allure.attachment_type.PNG)
            except Error:
                pass

    context.close()

    video_option = pytestconfig.getoption("--video")
    preserve_video = video_option == "on" or (
        failed and video_option == "retain-on-failure"
    )
    if preserve_video:
        for page in pages:
            video = page.video
            if not video:
                continue
            try:
                video_path = video.path()
                file_name = os.path.basename(video_path)
                video.save_as(
                    path=_build_artifact_test_folder(pytestconfig, request, file_name)
                )
                allure.attach.file(_build_artifact_test_folder(pytestconfig, request, file_name), 'video', allure.attachment_type.WEBM)
            except Error:
                # Silent catch empty videos.
                pass


def _build_snapshots_folder(request: pytest.FixtureRequest, folder_or_file_name=None, actual=False, diff=False):
    if actual and not folder_or_file_name:
        folder_or_file_name = f'{slugify(request.node.nodeid)}-actual.png'
    elif diff and not folder_or_file_name:
        folder_or_file_name = f'{slugify(request.node.nodeid)}-diff.png'
    else:
        folder_or_file_name = folder_or_file_name or f'{slugify(request.node.nodeid)}.png'
    return os.path.join(
        request.node.path.parent,
        f'{truncate_file_name(os.path.splitext(os.path.basename(request.node.path))[0])}-snapshots',
        f'{truncate_file_name(folder_or_file_name)}'
    )


def to_have_screenshot(request: pytest.FixtureRequest, page: Page,
                       folder_or_file_name=None, update=False, maxDiffPixelRatio=0, maxDiffPixels=None, threshold=0.2, **kwargs):
    raw_snapshot_folder = _build_snapshots_folder(request, folder_or_file_name)
    if not os.path.exists(raw_snapshot_folder):
        page.screenshot(path=raw_snapshot_folder, **kwargs)
        raise Exception(f"Error: A snapshot doesn't exist at {raw_snapshot_folder}, writing actual.")
    if update:
        page.screenshot(path=raw_snapshot_folder, **kwargs)
        return True
    raw_snapshot = Image.open(raw_snapshot_folder)
    actual_snapshot = Image.open(BytesIO(page.screenshot(**kwargs)))
    diff_snapshot = Image.new("RGBA", raw_snapshot.size)

    mismatch = pixelmatch(raw_snapshot, actual_snapshot, diff_snapshot, includeAA=True, threshold=threshold)
    if (maxDiffPixels and mismatch > maxDiffPixels) or (mismatch / reduce(operator.mul, raw_snapshot.size) > maxDiffPixelRatio):
        actual_snapshot_folder = _build_snapshots_folder(request, folder_or_file_name, actual=True)
        actual_snapshot.save(actual_snapshot_folder)
        diff_snapshot_folder = _build_snapshots_folder(request, folder_or_file_name, diff=True)
        diff_snapshot.save(diff_snapshot_folder)
        allure.attach.file(raw_snapshot_folder, name='Expected', attachment_type=allure.attachment_type.PNG)
        allure.attach.file(actual_snapshot_folder, name='Actual', attachment_type=allure.attachment_type.PNG)
        allure.attach.file(diff_snapshot_folder, name='Diff', attachment_type=allure.attachment_type.PNG)
        raise Exception(f"Screenshot comparison failed。\nExpected:{raw_snapshot_folder}\nReceived:{actual_snapshot_folder}\nDiff:{diff_snapshot_folder}")
    else:
        return True


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("allure-playwright", "Allure-Playwright")
    group.addoption(
        "--start-maximized",
        action="store_true",
        default=False,
        help="Browser maximized.",
    )
