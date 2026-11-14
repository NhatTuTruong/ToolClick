@extends('layout')
@section('title', 'Thống kê chạy')
@section('content')

<div class="kpis">
    <div class="kpi"><span>Tổng lần chạy</span><b>{{ number_format($total) }}</b></div>
    <div class="kpi"><span>Hôm nay</span><b>{{ number_format($today) }}</b></div>
    <div class="kpi"><span>Key đã ghi</span><b>{{ number_format($keys) }}</b></div>
    <div class="kpi"><span>Ads tìm thấy</span><b>{{ number_format($adsSum) }}</b></div>
    <div class="kpi"><span>Click OK</span><b>{{ number_format($clicksSum) }}</b></div>
</div>

<div class="card">
    <h1>Thống kê mỗi lần chạy</h1>
    <p class="hint">Keyword, domain click / không click, ghi chú key, thời gian, IP, số vòng SERP — mọi key. Lỗi ghi thống kê không ảnh hưởng kích hoạt hay chạy tool.</p>
    <form class="search" method="get">
        <input class="input" name="q" value="{{ $q }}" placeholder="Tìm key, ghi chú, keyword, domain, IP…">
        <input class="input" type="date" name="from" value="{{ $from }}" style="max-width:160px">
        <input class="input" type="date" name="to" value="{{ $to }}" style="max-width:160px">
        <button class="btn ghost" type="submit">Lọc</button>
    </form>

    <div style="overflow-x:auto">
        <table class="stats">
            <thead>
                <tr>
                    <th>Thời gian</th>
                    <th>Key / ghi chú</th>
                    <th>Keyword</th>
                    <th>Domain click</th>
                    <th>Domain không click</th>
                    <th>SERP</th>
                    <th>Ads tìm thấy</th>
                    <th>Click OK</th>
                    <th>IP</th>
                </tr>
            </thead>
            <tbody>
            @forelse($rows as $row)
                <tr>
                    <td>{{ $row->ran_at?->format('d/m/Y H:i:s') }}</td>
                    <td>
                        <div class="code">{{ $row->key_code ?: '—' }}</div>
                        <div class="sub">{{ $row->key_note ?: '—' }}</div>
                    </td>
                    <td class="cell">{{ $row->keywords ?: '—' }}<div class="sub">{{ $row->keyword_count }} từ</div></td>
                    <td class="cell">{{ $row->click_domains ?: '—' }}<div class="sub">{{ $row->click_domain_count }}</div></td>
                    <td class="cell">{{ $row->skip_domains ?: '—' }}<div class="sub">{{ $row->skip_domain_count }}</div></td>
                    <td>{{ $row->serp_rounds }}</td>
                    <td>{{ number_format($row->ads_found) }}</td>
                    <td>{{ number_format($row->clicks_ok) }}</td>
                    <td>
                        {{ $row->ip ?: '—' }}
                        <div class="sub">{{ $row->hostname ?: '' }}</div>
                    </td>
                </tr>
            @empty
                <tr><td colspan="9">Chưa có lần chạy nào.</td></tr>
            @endforelse
            </tbody>
        </table>
    </div>
    <div class="pager">{{ $rows->links() }}</div>
</div>
@endsection
