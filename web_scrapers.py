from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import time

from constants import CONTACTS_URL, CAREER_URL, CUSTOMERS_URL


async def wait_for_visible(locator, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        if await locator.is_visible():
            return True
        await asyncio.sleep(0.2)
    return False


async def scrape_city_addresses():
    url = CONTACTS_URL
    city_data = {}

    cities_container_selector = '.contacts-cities-container'
    button_selector = 'a'
    details_container_selector = '.selected-city-details'

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(url, wait_until='networkidle', timeout=10000)

        await page.wait_for_selector(cities_container_selector, state='visible', timeout=3000)
        cities_container = page.locator(cities_container_selector)

        city_buttons_locator = cities_container.locator(button_selector)
        button_count = await city_buttons_locator.count()

        for i in range(button_count):
            current_buttons_locator = cities_container.locator(button_selector)
            button = current_buttons_locator.nth(i)

            city_name = await button.text_content()
            city_name = city_name.strip()

            await button.click(timeout=1000)
            await asyncio.sleep(1)

            await page.locator(details_container_selector).wait_for(state='visible', timeout=1500)

            details_locator = page.locator(details_container_selector)
            details_text = await details_locator.evaluate('element => element.innerText', timeout=5000)
            city_data[city_name] = details_text.strip().replace('\n', ' ')

        await browser.close()

    return city_data

    
async def scrape_customer_details():
    url = CUSTOMERS_URL
    customer_data = []

    pagination_container_selector = '.customers-pagination__pages'
    button_selector = '.customers-pagination__link'
    customers_container_selector = '.customers-list'
    customers_list_block_selector = '.customers-list__block'
    customers_modal_content_selector = '.customer-modal__content-inner'
    close_button_selector = '.customer-modal__close'

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(url, wait_until='networkidle', timeout=10000)

        await page.wait_for_selector(pagination_container_selector, state='visible', timeout=5000)
        pagination_container = page.locator(pagination_container_selector)

        pagination_buttons_locator = pagination_container.locator(button_selector)
        button_count = await pagination_buttons_locator.count()

        for i in range(button_count):
            current_buttons_locator = pagination_container.locator(button_selector)
            button = current_buttons_locator.nth(i)

            await button.click(timeout=3000)
            await page.wait_for_load_state('networkidle', timeout=1000)

            await page.locator(customers_container_selector).wait_for(state='visible', timeout=10000)
            customers_container = page.locator(customers_container_selector)
            customer_block_locator = customers_container.locator(customers_list_block_selector)
            customers_count = await customer_block_locator.count()

            for j in range(customers_count):
                current_customers_locator = customers_container.locator(customers_list_block_selector)
                block = current_customers_locator.nth(j)

                await block.scroll_into_view_if_needed()
                await block.click(timeout=3000)

                try:
                    locator = page.locator(customers_modal_content_selector)
                    visible = await wait_for_visible(locator)
                    if not visible:
                        continue

                    details_locator = page.locator(customers_modal_content_selector)
                    details_text = await details_locator.evaluate('element => element.innerText')
                    customer_data.append(details_text.strip().replace('\n', ' '))

                    close_button_locator = page.locator(close_button_selector)
                    await close_button_locator.click(timeout=3000)

                    await page.locator(customers_modal_content_selector).wait_for(state='hidden', timeout=10000)

                except PlaywrightTimeoutError:
                    continue

        await browser.close()

    return customer_data


async def scrape_career_details():
    url = CAREER_URL
    email_container_selector = '.InfoBLock__info-info'

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(url, wait_until='networkidle', timeout=10000)

        await page.wait_for_selector(email_container_selector, state='visible', timeout=3000)
        email_container = page.locator(email_container_selector)

        details_text = await email_container.evaluate('element => element.innerText', timeout=5000)
        data = details_text.strip().replace('\n', ' ')

        await browser.close()

    return data