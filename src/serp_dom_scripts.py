"""Script evaluate trên SERP — organic / sponsored tách bạch, không quét cả document.body."""

from __future__ import annotations

from .serp_ad_guard import JS_SERP_AD_HELPERS_IIFE


def _dom_utils_js() -> str:
    return f"""
      const helpers = {JS_SERP_AD_HELPERS_IIFE};
      const {{ hrefIsSponsoredAdUrl, elementIsInsideSponsoredBlock }} = helpers;
      const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim();

      function cleanAdTitle(raw) {{
        let t = norm(raw);
        const idx = t.toLowerCase().indexOf('http');
        if (idx > 8) t = t.slice(0, idx).trim();
        return t;
      }}

      function isJunkTitle(title) {{
        const s = (title || '').trim().toLowerCase();
        if (s.length < 12) return true;
        if (/^translate\\b/.test(s)) return true;
        if (/^\\d+\\s+answers?\\b/.test(s)) return true;
        if (/^more\\b/.test(s)) return true;
        if (/^cached\\b/.test(s)) return true;
        return false;
      }}

      function mainAdLink(block) {{
        return (
          block.querySelector('a[href]:has(h3)') ||
          block.querySelector('a[href*="/aclk"]') ||
          block.querySelector('a[href*="/goto"]') ||
          block.querySelector('a[data-rw][href]')
        );
      }}

      function titleMatches(a, b) {{
        const x = norm(a).toLowerCase();
        const y = norm(b).toLowerCase();
        if (!x || !y) return false;
        const x45 = x.slice(0, 45);
        const y45 = y.slice(0, 45);
        if (x45 === y45 || x.includes(y45) || y.includes(x45)) return true;
        const x30 = x.slice(0, 30);
        const y30 = y.slice(0, 30);
        return x30.length >= 18 && x30 === y30;
      }}

      function hrefRoughMatch(a, b) {{
        const na = norm(a).split('#')[0];
        const nb = norm(b).split('#')[0];
        if (!na || !nb) return false;
        if (na === nb) return true;
        try {{
          const ua = new URL(na);
          const ub = new URL(nb);
          if (ua.pathname.includes('/aclk') && ub.pathname.includes('/aclk')) {{
            const adA = ua.searchParams.get('adurl') || '';
            const adB = ub.searchParams.get('adurl') || '';
            if (adA && adB && adA === adB) return true;
          }}
          if (ua.hostname && ua.hostname === ub.hostname && ua.pathname === ub.pathname) {{
            return true;
          }}
        }} catch (e) {{}}
        return false;
      }}

      function resolveSponsoredPick(list, payload) {{
        const rank = payload.rank || 1;
        const href = payload.href || '';
        const title = payload.title || '';
        if (href) {{
          const byHref = list.find(r => hrefRoughMatch(r.href || r.destination_url, href));
          if (byHref) return byHref;
        }}
        if (title) {{
          const byTitle = list.find(r => titleMatches(r.title, title));
          if (byTitle) return byTitle;
        }}
        return list[rank - 1] || null;
      }}

      function adBlockElements() {{
        const blockSelectors = [
          '#tads [data-text-ad]',
          '#tads .uEierd',
          '#tadsb [data-text-ad]',
          '#tadsb .uEierd',
          '#bottomads [data-text-ad]',
          '#bottomads .uEierd',
          '[data-text-ad="1"]',
          '[data-text-ad]',
          'div.uEierd',
          'div.v5yQqb',
        ].join(',');
        const set = new Set();
        document.querySelectorAll(blockSelectors).forEach(el => set.add(el));
        document.querySelectorAll('#tads > div, #tadsb > div, #bottomads > div').forEach(el => {{
          if (mainAdLink(el)) set.add(el);
        }});
        return [...set];
      }}

      function collectSponsoredRows() {{
        const seen = new Set();
        const results = [];
        const blocks = adBlockElements();
        for (const block of blocks) {{
          const anchor = mainAdLink(block);
          if (!anchor) continue;
          const href = anchor.href || '';
          if (!href || href.includes('google.com/search')) continue;
          if (!hrefIsSponsoredAdUrl(href) && !block.matches('[data-text-ad], .uEierd, .v5yQqb')) continue;

          const h3 = anchor.querySelector('h3') || block.querySelector('h3');
          const title = cleanAdTitle(h3 ? h3.innerText : anchor.innerText);
          if (isJunkTitle(title)) continue;

          const cite = block.querySelector('cite, .VuuXrf, .x2VHCd');
          let label = 'Sponsored';
          for (const s of block.querySelectorAll('span, div, label')) {{
            const t = norm(s.innerText || s.textContent || '').toLowerCase();
            if (t === 'quảng cáo' || t === 'sponsored' || t.includes('quảng cáo')) {{
              label = norm(s.innerText || s.textContent || '') || label;
              break;
            }}
          }}

          const key = href + '|' + title.slice(0, 80);
          if (seen.has(key)) continue;
          seen.add(key);
          results.push({{
            title,
            href,
            display_url: cite ? norm(cite.innerText) : '',
            destination_url: href,
            label,
            snippet: norm(block.innerText).slice(0, 500),
          }});
        }}
        return results;
      }}

      function findSponsoredAnchorForPick(pick) {{
        if (!pick) return null;
        const blocks = adBlockElements();
        for (const block of blocks) {{
          const anchor = mainAdLink(block);
          if (!anchor) continue;
          const h3 = anchor.querySelector('h3') || block.querySelector('h3');
          const title = cleanAdTitle(h3 ? h3.innerText : anchor.innerText);
          if (isJunkTitle(title)) continue;
          const href = anchor.href || '';
          const pickHref = pick.href || pick.destination_url || '';
          const titleOk = pick.title && titleMatches(title, pick.title);
          const hrefOk = pickHref && hrefRoughMatch(href, pickHref);
          if (!titleOk && !hrefOk) continue;
          anchor.scrollIntoView({{ block: 'center' }});
          return anchor;
        }}
        return null;
      }}

      function clickSponsoredPick(pick) {{
        const anchor = findSponsoredAnchorForPick(pick);
        if (!anchor) return {{ clicked: false, reason: 'anchor_gone' }};
        const h3 = anchor.querySelector('h3') || anchor.closest('[data-text-ad], .uEierd')?.querySelector('h3');
        const title = cleanAdTitle(h3 ? h3.innerText : anchor.innerText);
        anchor.click();
        return {{
          clicked: true,
          reason: '',
          title,
          picked_href: anchor.href,
        }};
      }}

      function collectOrganicRows() {{
        const root = document.querySelector('#rso') || document.querySelector('#search');
        if (!root) return [];

        const seen = new Set();
        const out = [];
        for (const anchor of root.querySelectorAll('a:has(h3)')) {{
          if (anchor.closest('#tads, #tadsb, #bottomads')) continue;
          if (elementIsInsideSponsoredBlock(anchor)) continue;
          if (hrefIsSponsoredAdUrl(anchor.href)) continue;

          const href = anchor.href || '';
          if (!href || href.includes('google.com/search')) continue;
          if (href.includes('webcache') || href.includes('translate.google')) continue;

          const h3 = anchor.querySelector('h3');
          const title = h3 ? norm(h3.innerText) : norm(anchor.innerText);
          if (isJunkTitle(title)) continue;

          const block = anchor.closest('div.g, div[data-sokoban-container]');
          const cite = block ? block.querySelector('cite') : null;
          const display = cite ? norm(cite.innerText) : '';

          const key = href.split('#')[0];
          if (seen.has(key)) continue;
          seen.add(key);
          out.push({{ title, href, display_url: display }});
        }}
        return out;
      }}
    """


def script_extract_organic_anchors() -> str:
    return f"""
    () => {{
      {_dom_utils_js()}
      return collectOrganicRows();
    }}
    """


def script_extract_sponsored_anchors() -> str:
    return f"""
    () => {{
      {_dom_utils_js()}
      return collectSponsoredRows();
    }}
    """


def script_list_sponsored_anchors() -> str:
    return f"""
    () => {{
      {_dom_utils_js()}
      return collectSponsoredRows().map(r => ({{ href: r.href || r.destination_url, title: r.title }}));
    }}
    """


def script_click_organic_href_if_safe() -> str:
    return f"""
    (href) => {{
      {_dom_utils_js()}
      const root = document.querySelector('#rso') || document.body;

      for (const anchor of root.querySelectorAll('a[href]')) {{
        if (anchor.href !== href) continue;
        if (elementIsInsideSponsoredBlock(anchor) || hrefIsSponsoredAdUrl(anchor.href)) {{
          return {{ clicked: false, blocked: true, reason: 'sponsored_ad' }};
        }}
        anchor.scrollIntoView({{ block: 'center' }});
        anchor.click();
        return {{ clicked: true, blocked: false, reason: '' }};
      }}
      return {{ clicked: false, blocked: false, reason: 'not_found' }};
    }}
    """


def script_click_sponsored_target_for_test() -> str:
    """Click quảng cáo trong #tads / block ads — khớp href/title trước rank."""
    return f"""
    (payload) => {{
      {_dom_utils_js()}
      const list = collectSponsoredRows();
      const pick = resolveSponsoredPick(list, payload);
      if (!pick) {{
        return {{ clicked: false, reason: 'not_found', listed: list.length, title: payload.title || '' }};
      }}
      const out = clickSponsoredPick(pick);
      return {{ ...out, listed: list.length }};
    }}
    """


def script_sponsored_target_visible() -> str:
    """payload {{title, href, rank}} — quảng cáo còn trên DOM hiện tại."""
    return f"""
    (payload) => {{
      {_dom_utils_js()}
      const list = collectSponsoredRows();
      return !!resolveSponsoredPick(list, payload);
    }}
    """


def script_scroll_serp_for_ads() -> str:
    return """
    async () => {
      window.scrollTo(0, document.body.scrollHeight);
      await new Promise(r => setTimeout(r, 550));
      window.scrollTo(0, 0);
      await new Promise(r => setTimeout(r, 350));
    }
    """


def script_find_sponsored_anchor_element() -> str:
    """Trả về thẻ <a> quảng cáo — dùng với evaluate_handle + click tab mới."""
    return f"""
    (payload) => {{
      {_dom_utils_js()}
      const list = collectSponsoredRows();
      const pick = resolveSponsoredPick(list, payload);
      if (!pick) return null;
      return findSponsoredAnchorForPick(pick);
    }}
    """
