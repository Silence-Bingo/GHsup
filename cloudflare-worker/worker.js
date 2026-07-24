/**
 * GitHub 加速器 - Cloudflare Worker
 * 
 * 功能：作为 DNS-over-HTTPS 代理，解析 GitHub 域名
 * 部署：在 Cloudflare Dashboard 创建 Worker，复制此代码
 * 
 * 使用方式：
 *   GET https://your-worker.workers.dev/?domain=github.com
 * 
 * 返回：
 *   {"domain":"github.com","ip":"140.82.121.3","latency_ms":12}
 */

// 允许的域名列表（防止滥用）
const ALLOWED_DOMAINS = [
  'github.com',
  'github.global.ssl.fastly.net',
  'assets-cdn.github.com',
  'raw.githubusercontent.com',
  'gist.githubusercontent.com',
  'codeload.github.com',
  'api.github.com',
  'github.githubassets.com',
  'favicons.githubusercontent.com',
];

// CORS 头
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env, ctx) {
    // 处理 CORS 预检请求
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const domain = url.searchParams.get('domain');

    // 验证参数
    if (!domain) {
      return jsonResponse({ error: 'Missing domain parameter' }, 400);
    }

    // 验证域名
    if (!ALLOWED_DOMAINS.includes(domain)) {
      return jsonResponse({ error: 'Domain not allowed' }, 403);
    }

    try {
      // 使用 Cloudflare 的 DNS-over-HTTPS 解析域名
      const startTime = Date.now();
      const dnsResponse = await fetch(
        `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(domain)}&type=A`,
        {
          headers: {
            'Accept': 'application/dns-json',
          },
        }
      );
      const latency = Date.now() - startTime;

      if (!dnsResponse.ok) {
        return jsonResponse({ error: 'DNS query failed' }, 502);
      }

      const dnsData = await dnsResponse.json();

      // 提取 IP 地址
      if (dnsData.Answer && dnsData.Answer.length > 0) {
        const ips = dnsData.Answer
          .filter(answer => answer.type === 1) // A 记录
          .map(answer => answer.data);

        if (ips.length > 0) {
          return jsonResponse({
            domain: domain,
            ip: ips[0],
            all_ips: ips,
            latency_ms: latency,
          });
        }
      }

      return jsonResponse({ error: 'No A record found' }, 404);

    } catch (error) {
      return jsonResponse({ error: error.message }, 500);
    }
  },
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}
