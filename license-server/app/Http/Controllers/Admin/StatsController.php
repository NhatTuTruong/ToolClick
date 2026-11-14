<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\LicenseRunStat;
use Illuminate\Http\Request;

class StatsController extends Controller
{
    public function index(Request $request)
    {
        $q = trim((string) $request->get('q', ''));
        $from = $request->get('from');
        $to = $request->get('to');

        $rows = LicenseRunStat::query()
            ->when($q !== '', function ($query) use ($q) {
                $query->where(function ($inner) use ($q) {
                    $inner->where('key_code', 'like', '%'.$q.'%')
                        ->orWhere('key_note', 'like', '%'.$q.'%')
                        ->orWhere('keywords', 'like', '%'.$q.'%')
                        ->orWhere('click_domains', 'like', '%'.$q.'%')
                        ->orWhere('skip_domains', 'like', '%'.$q.'%')
                        ->orWhere('ip', 'like', '%'.$q.'%');
                });
            })
            ->when($from, fn ($query) => $query->whereDate('ran_at', '>=', $from))
            ->when($to, fn ($query) => $query->whereDate('ran_at', '<=', $to))
            ->latest('ran_at')
            ->latest('id')
            ->paginate(30)
            ->withQueryString();

        $base = LicenseRunStat::query()
            ->when($q !== '', function ($query) use ($q) {
                $query->where(function ($inner) use ($q) {
                    $inner->where('key_code', 'like', '%'.$q.'%')
                        ->orWhere('key_note', 'like', '%'.$q.'%')
                        ->orWhere('keywords', 'like', '%'.$q.'%')
                        ->orWhere('click_domains', 'like', '%'.$q.'%')
                        ->orWhere('skip_domains', 'like', '%'.$q.'%')
                        ->orWhere('ip', 'like', '%'.$q.'%');
                });
            })
            ->when($from, fn ($query) => $query->whereDate('ran_at', '>=', $from))
            ->when($to, fn ($query) => $query->whereDate('ran_at', '<=', $to));

        $today = (clone $base)->whereDate('ran_at', now()->toDateString())->count();
        $total = (clone $base)->count();
        $keys = (int) (clone $base)
            ->whereNotNull('key_code')
            ->selectRaw('count(distinct key_code) as c')
            ->value('c');
        $adsSum = (int) (clone $base)->sum('ads_found');
        $clicksSum = (int) (clone $base)->sum('clicks_ok');

        return view('stats.index', compact(
            'rows', 'q', 'from', 'to', 'today', 'total', 'keys', 'adsSum', 'clicksSum'
        ));
    }
}
