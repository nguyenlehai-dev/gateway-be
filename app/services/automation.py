import asyncio
import json
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Error as PlaywrightError, Locator, Page, TimeoutError, async_playwright

from app.core.config import get_settings
from app.models import AutomationJob, Category, JobStatus, Profile
from app.schemas import AutomationPreview


class AutomationService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider_defaults: dict[Category, dict[str, Any]] = {
            Category.GROK: {
                "default_url": "https://grok.com/",
                "default_cookie_url": "https://grok.com/",
                "default_cookie_domain": ".grok.com",
                "steps": [
                    "Launch browser with Playwright in headless mode",
                    "Inject Grok cookies for grok.com",
                    "Open image or video generation surface",
                    "Submit prompt and wait for generated asset",
                ],
                "selectors": {
                    "prompt": "textarea, [contenteditable='true'], [role='textbox']",
                    "submit": None,
                    "result": "img, video, a[href*='blob:'], a[href*='http']",
                    "ready": "body",
                },
            },
            Category.FLOW: {
                "default_url": "https://labs.google/fx/tools/flow",
                "default_cookie_url": "https://labs.google/",
                "default_cookie_domain": ".google.com",
                "steps": [
                    "Launch browser with Playwright in headless mode",
                    "Inject Google Labs Flow cookies",
                    "Open Flow workspace and submit prompt",
                    "Capture generated image or video result",
                ],
                "selectors": {
                    "prompt": "textarea, [contenteditable='true'], [role='textbox']",
                    "submit": "button[type=submit], button[aria-label*='Generate'], button:has-text('Generate')",
                    "result": "img, video, a[href]",
                    "ready": "body",
                },
            },
            Category.DREAMINA: {
                "default_url": "https://dreamina.capcut.com/",
                "default_cookie_url": "https://dreamina.capcut.com/",
                "default_cookie_domain": ".capcut.com",
                "steps": [
                    "Launch browser with Playwright in headless mode",
                    "Inject Dreamina cookies",
                    "Navigate to Dreamina creative flow",
                    "Submit prompt and collect outputs",
                ],
                "selectors": {
                    "prompt": "textarea",
                    "submit": None,
                    "result": None,
                    "ready": None,
                },
            },
        }

    def preview_for_profile(self, profile: Profile) -> AutomationPreview:
        provider_config = self.provider_defaults[profile.category]
        launch_options = {
            "headless": profile.headless,
            "proxy": profile.proxy.host if profile.proxy else None,
            "viewport": {"width": profile.screen_width, "height": profile.screen_height},
            "locale": profile.locale,
            "timezone_id": profile.timezone,
            "user_agent": profile.user_agent,
            "timeout_ms": self.settings.playwright_timeout_ms,
        }
        return AutomationPreview(
            provider=profile.category,
            headless=profile.headless,
            concurrency=profile.concurrency,
            launch_options=launch_options,
            steps=provider_config["steps"],
        )

    def run_job(self, job: AutomationJob) -> dict[str, Any]:
        if job.profile.category == Category.GROK:
            return asyncio.run(self._run_provider_job(job, Category.GROK))
        if job.profile.category == Category.FLOW:
            return asyncio.run(self._run_provider_job(job, Category.FLOW))
        raise NotImplementedError("Dreamina runner will be added in a later step.")

    async def _run_provider_job(self, job: AutomationJob, provider: Category) -> dict[str, Any]:
        profile = job.profile
        metadata = dict(job.metadata_json or {})
        artifact_dir = self._artifact_dir(profile, job)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        provider_config = self.provider_defaults[provider]
        start_url = str(metadata.get("start_url") or metadata.get("workspace_url") or provider_config["default_url"])
        default_selectors = provider_config["selectors"]
        selectors = {
            "prompt": metadata.get("prompt_selector", default_selectors["prompt"]),
            "submit": metadata.get("submit_selector", default_selectors["submit"]),
            "result": metadata.get("result_selector", default_selectors["result"]),
            "ready": metadata.get("ready_selector", default_selectors["ready"]),
        }
        execution_log: list[str] = []

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=profile.headless)
            context = await browser.new_context(**self._context_options(profile))
            try:
                await self._apply_cookies(context, profile, provider)
                page = await context.new_page()
                page.set_default_timeout(self.settings.playwright_timeout_ms)

                execution_log.append(f"goto:{start_url}")
                await page.goto(start_url, wait_until="domcontentloaded")
                await page.wait_for_load_state("networkidle")

                if selectors["ready"]:
                    execution_log.append(f"wait_for_ready:{selectors['ready']}")
                    await page.wait_for_selector(str(selectors["ready"]))

                execution_log.append(f"fill_prompt:{selectors['prompt']}")
                prompt_locator = await self._pick_visible_locator(page, str(selectors["prompt"]))
                await prompt_locator.fill(job.prompt)

                if selectors["submit"]:
                    execution_log.append(f"click_submit:{selectors['submit']}")
                    submit_locator = await self._pick_visible_locator(page, str(selectors["submit"]))
                    await submit_locator.click()
                else:
                    execution_log.append("submit_with_enter")
                    await prompt_locator.press("Control+Enter")

                output_url = await self._collect_result(page, selectors, artifact_dir, execution_log)
                await context.storage_state(path=str(artifact_dir / "storage-state.json"))
                await page.screenshot(path=str(artifact_dir / "final-page.png"), full_page=True)
                return {
                    "status": JobStatus.COMPLETED,
                    "output_url": output_url,
                    "metadata_json": {
                        **metadata,
                        "provider": provider.value,
                        "artifact_dir": str(artifact_dir),
                        "execution_log": execution_log,
                    },
                }
            except PlaywrightError as exc:
                try:
                    await page.screenshot(path=str(artifact_dir / "failed-page.png"), full_page=True)
                except Exception:
                    pass
                await context.storage_state(path=str(artifact_dir / "failed-storage-state.json"))
                return {
                    "status": JobStatus.FAILED,
                    "error_message": str(exc),
                    "metadata_json": {
                        **metadata,
                        "provider": provider.value,
                        "artifact_dir": str(artifact_dir),
                        "execution_log": execution_log,
                    },
                }
            finally:
                await context.close()
                await browser.close()

    def _context_options(self, profile: Profile) -> dict[str, Any]:
        options: dict[str, Any] = {
            "viewport": {"width": profile.screen_width, "height": profile.screen_height},
            "locale": profile.locale or None,
            "timezone_id": profile.timezone or None,
            "user_agent": profile.user_agent or None,
        }
        if profile.proxy:
            proxy_url = f"{profile.proxy.protocol}://{profile.proxy.host}:{profile.proxy.port}"
            if profile.proxy.username and profile.proxy.password:
                proxy_url = (
                    f"{profile.proxy.protocol}://{profile.proxy.username}:{profile.proxy.password}"
                    f"@{profile.proxy.host}:{profile.proxy.port}"
                )
            options["proxy"] = {"server": proxy_url}
        return {key: value for key, value in options.items() if value is not None}

    async def _apply_cookies(self, context: BrowserContext, profile: Profile, provider: Category) -> None:
        if not profile.cookies:
            return
        provider_config = self.provider_defaults[provider]
        cookies = []
        for item in profile.cookies:
            name = item.get("name")
            value = item.get("value")
            if not name or value is None:
                continue

            cookie: dict[str, Any] = {
                "name": str(name),
                "value": str(value),
            }
            domain = item.get("domain")
            path = item.get("path") or "/"
            if domain:
                cookie["domain"] = str(domain)
                cookie["path"] = str(path)
            else:
                fallback_url = item.get("url") or provider_config["default_cookie_url"]
                cookie["url"] = str(fallback_url)

            if "secure" in item:
                cookie["secure"] = bool(item["secure"])
            if "httpOnly" in item:
                cookie["httpOnly"] = bool(item["httpOnly"])
            if item.get("sameSite") in {"Strict", "Lax", "None"}:
                cookie["sameSite"] = item["sameSite"]
            expires = item.get("expires")
            if isinstance(expires, (int, float)):
                cookie["expires"] = expires
            if "domain" not in cookie and "url" not in cookie:
                cookie["domain"] = provider_config["default_cookie_domain"]
                cookie["path"] = str(path)
            cookies.append(cookie)
        await context.add_cookies(cookies)

    async def _collect_result(
        self,
        page: Page,
        selectors: dict[str, Any],
        artifact_dir: Path,
        execution_log: list[str],
    ) -> str:
        if selectors["result"]:
            execution_log.append(f"wait_for_result:{selectors['result']}")
            locator = await self._pick_visible_locator(page, str(selectors["result"]), timeout_ms=30_000)
            text = await locator.text_content()
            href = await locator.get_attribute("href")
            src = await locator.get_attribute("src")
            result = href or src or text or str(artifact_dir / "final-page.png")
            (artifact_dir / "result.json").write_text(json.dumps({"result": result}, indent=2))
            return result

        execution_log.append("result_selector_not_provided")
        return str(artifact_dir / "final-page.png")

    async def _pick_visible_locator(self, page: Page, selector: str, timeout_ms: int | None = None) -> Locator:
        locator = page.locator(selector)
        max_wait = timeout_ms or self.settings.playwright_timeout_ms
        deadline = asyncio.get_running_loop().time() + (max_wait / 1000)
        while asyncio.get_running_loop().time() < deadline:
            count = await locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if not await candidate.is_visible():
                        continue
                    if await candidate.is_disabled():
                        continue
                    return candidate
                except PlaywrightError:
                    continue
            await page.wait_for_timeout(250)
        raise TimeoutError(f"No visible element found for selector: {selector}")

    def _artifact_dir(self, profile: Profile, job: AutomationJob) -> Path:
        base = Path(profile.cache_path) if profile.cache_path else Path.cwd() / "artifacts"
        return base / profile.category.value / f"profile-{profile.id}" / f"job-{job.public_id}"
