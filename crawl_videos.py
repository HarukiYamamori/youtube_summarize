from playwright.sync_api import sync_playwright


def fetch_channel_data(channel_url):
    video_info_list = []
    channel_name = "チャンネル名が見つかりません"

    with sync_playwright() as p:
        # Chromiumブラウザを起動（ヘッドレスモード）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # YouTubeのチャンネル動画ページを開く
        page.goto(channel_url)
        page.wait_for_load_state("networkidle")

        # 動画一覧が表示されるまで少し待つ
        page.wait_for_selector(".ytd-rich-grid-media a#thumbnail", timeout=60000)

        # Extract video links
        video_cover_els = page.query_selector_all(".ytd-rich-grid-media")
        for video_el in video_cover_els:
            thumbnail_el = video_el.query_selector("a#thumbnail")
            if thumbnail_el:
                link_txt = thumbnail_el.get_attribute("href")
                if link_txt and "/watch?" in link_txt:
                    uploaded_date_el = video_el.query_selector(
                        "#metadata-line .inline-metadata-item:nth-of-type(2)"
                    )
                    uploaded_date = (
                        uploaded_date_el.text_content().strip()
                        if uploaded_date_el
                        else "不明"
                    )
                    if (
                        "時間前" in uploaded_date
                        or "分前" in uploaded_date
                        or "秒前" in uploaded_date
                        or "seconds ago" in uploaded_date
                        or "minutes ago" in uploaded_date
                        or "hours ago" in uploaded_date
                    ):
                        title = video_el.query_selector("#video-title").text_content()
                        videos_info = {
                            "title": title,
                            "link": f"https://www.youtube.com{link_txt}",
                            "uploaded_date": uploaded_date,
                        }
                        video_info_list.append(videos_info)

        # Extract channel name
        channel_name_selector = "h1[aria-label]"
        page.wait_for_selector(channel_name_selector, timeout=60000)
        channel_name_element = page.query_selector(channel_name_selector)
        if channel_name_element:
            channel_name = channel_name_element.text_content().strip()

        browser.close()

    return video_info_list, channel_name


if __name__ == "__main__":
    video_links, channel_name = fetch_channel_data("")
    print("Channel Name:", channel_name)
    print("Video Links:", video_links)
