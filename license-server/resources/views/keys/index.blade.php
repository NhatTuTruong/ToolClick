@extends('layout')
@section('title', 'Key bản quyền')
@section('content')

<div class="card">
    <h1>Thêm hoặc cập nhật nhanh 1 key</h1>
    <p class="hint">Tạo key mới hoặc ghi đè key đã có (cùng mã key). Điền đủ hạn mức. Net được phép (tuỳ chọn).</p>
    <form method="post" action="{{ route('keys.upsert') }}" id="create-form">
        @csrf
        <label class="lbl">Thông tin key</label>
        <div class="row" style="margin-bottom: 8px;">
            <div style="flex:1">
                <label class="lbl">Key bản quyền</label>
                <input class="input" id="code" name="code" placeholder="TCL1-XXXX-XXXX-XXXX" value="{{ old('code') }}">
            </div>
            <div style="display:flex;align-items:flex-end">
                <button class="btn orange" type="button" id="btn-gen">Tạo mã</button>
            </div>
        </div>
        <div class="grid-4">
            <div>
                <label class="lbl">Giới hạn record / ngày</label>
                <input class="input" type="number" name="daily_record_limit" min="0" value="{{ old('daily_record_limit', 500) }}" required>
            </div>
            <div>
                <label class="lbl">Số máy tối đa</label>
                <input class="input" type="number" name="max_machines" min="1" value="{{ old('max_machines', 2) }}" required>
            </div>
            <div>
                <label class="lbl">Hạn dùng</label>
                <input class="input" type="date" name="expires_at" value="{{ old('expires_at') }}">
            </div>
            <div>
                <label class="lbl">Ghi chú</label>
                <input class="input" name="note" placeholder="Tuỳ chọn" value="{{ old('note') }}">
            </div>
        </div>
        <div style="margin-top:12px">
            <label class="lbl">Net / ghi chú tính năng</label>
            <input class="input" name="net" placeholder="Tuỳ chọn" value="{{ old('net') }}">
        </div>
        <div style="margin-top:14px">
            <button class="btn blue" type="submit">Lưu key</button>
        </div>
    </form>
</div>

<form class="search" method="get">
    <input class="input" name="q" value="{{ $q }}" placeholder="Tìm key, ghi chú, net…">
    <button class="btn ghost" type="submit">Tìm</button>
</form>

<div class="key-head">
    <div>ID</div>
    <div>Key</div>
    <div>Trạng thái</div>
    <div>Máy active</div>
    <div>Record/ngày</div>
    <div>Số máy max</div>
    <div>Net</div>
    <div>Hạn dùng</div>
</div>

@forelse($keys as $key)
<div class="card key-block">
    <div class="key-meta">
        <div>{{ $key->id }}</div>
        <div>
            <div class="code">{{ $key->code }}</div>
            <div class="sub">{{ $key->note ?: '—' }}</div>
        </div>
        <div>
            @if($key->isActive())
                <span class="badge on">Hoạt động</span>
            @else
                <span class="badge off">{{ $key->status === 'paused' ? 'Tạm khóa' : 'Hết hạn' }}</span>
            @endif
        </div>
        <div>{{ $key->machines_active_count }}</div>
        <div>{{ number_format($key->daily_record_limit) }}</div>
        <div>{{ $key->max_machines }}</div>
        <div>{{ $key->net ?: '—' }}</div>
        <div>{{ $key->expires_at?->format('d/m/Y') ?: '—' }}</div>
    </div>

    <form class="edit grid-5" method="post" action="{{ route('keys.update', $key) }}">
        @csrf
        @method('PATCH')
        <div>
            <label class="lbl">Trạng thái</label>
            <select name="status">
                <option value="active" @selected($key->status === 'active')>Hoạt động</option>
                <option value="paused" @selected($key->status === 'paused')>Tạm khóa</option>
            </select>
        </div>
        <div>
            <label class="lbl">Record/ngày</label>
            <input class="input" type="number" name="daily_record_limit" min="0" value="{{ $key->daily_record_limit }}">
        </div>
        <div>
            <label class="lbl">Số máy max</label>
            <input class="input" type="number" name="max_machines" min="1" value="{{ $key->max_machines }}">
        </div>
        <div>
            <label class="lbl">Hạn dùng</label>
            <input class="input" type="date" name="expires_at" value="{{ $key->expires_at?->toDateString() }}">
        </div>
        <div>
            <label class="lbl">Ghi chú</label>
            <input class="input" name="note" value="{{ $key->note }}">
        </div>
        <button class="btn blue" type="submit">Lưu</button>
        <div style="grid-column: 1 / -2">
            <label class="lbl">Net &amp; tính năng</label>
            <input class="input" name="net" value="{{ $key->net }}">
        </div>
        <button class="btn danger" type="submit" form="del-{{ $key->id }}">Xóa</button>
    </form>
    <form id="del-{{ $key->id }}" method="post" action="{{ route('keys.destroy', $key) }}" onsubmit="return confirm('Xóa key này và mọi máy đã gắn?')">
        @csrf
        @method('DELETE')
    </form>

    @if($key->activeMachines->count())
    <div class="machines">
        <table>
            <thead>
                <tr>
                    <th>Máy</th>
                    <th>Hostname</th>
                    <th>OS</th>
                    <th>Lần cuối</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
            @foreach($key->activeMachines as $m)
                <tr>
                    <td>{{ \Illuminate\Support\Str::limit($m->machine_id, 22) }}</td>
                    <td>{{ $m->hostname ?: '—' }}</td>
                    <td>{{ $m->os ?: '—' }}</td>
                    <td>{{ $m->last_seen_at?->format('d/m/Y H:i') ?: '—' }}</td>
                    <td>
                        <form method="post" action="{{ route('machines.revoke', $m) }}" onsubmit="return confirm('Gỡ máy này khỏi key?')">
                            @csrf
                            @method('DELETE')
                            <button class="btn ghost" type="submit">Gỡ máy</button>
                        </form>
                    </td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
    @endif
</div>
@empty
<div class="card">Chưa có key nào.</div>
@endforelse

<div class="pager">{{ $keys->links() }}</div>
@endsection

@push('scripts')
<script>
document.getElementById('btn-gen').addEventListener('click', async () => {
  const r = await fetch(@json(route('keys.generate')), {
    method: 'POST',
    headers: {
      'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content,
      'Accept': 'application/json',
    },
  });
  const data = await r.json();
  if (data.code) document.getElementById('code').value = data.code;
});
</script>
@endpush
