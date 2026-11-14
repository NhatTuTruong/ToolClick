@extends('layout')
@section('title', 'Đăng nhập')
@section('content')
<div class="card login-box">
    <h1>Quản lý key bản quyền</h1>
    <p class="hint">Đăng nhập admin để tạo và giới hạn máy cho từng key.</p>
    <form method="post" action="{{ route('login.attempt') }}">
        @csrf
        <label class="lbl">Email</label>
        <input class="input" type="email" name="email" value="{{ old('email') }}" required style="margin-bottom:12px">
        <label class="lbl">Mật khẩu</label>
        <input class="input" type="password" name="password" required style="margin-bottom:16px">
        <button class="btn orange" type="submit">Đăng nhập</button>
    </form>
</div>
@endsection
