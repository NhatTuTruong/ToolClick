<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title', 'Key bản quyền') — ToolClick</title>
    <link rel="stylesheet" href="{{ asset('css/admin.css') }}">
</head>
<body>
    <header class="top">
        <div class="top-inner">
            <div class="brand">ToolClick <span>License</span></div>
            @if(session('admin_ok'))
                <nav class="nav">
                    <a href="{{ route('keys.index') }}" class="{{ request()->routeIs('keys.*') ? 'on' : '' }}">Key</a>
                    <a href="{{ route('stats.index') }}" class="{{ request()->routeIs('stats.*') ? 'on' : '' }}">Thống kê</a>
                    <form method="post" action="{{ route('logout') }}">
                        @csrf
                        <button class="btn ghost" type="submit">Đăng xuất</button>
                    </form>
                </nav>
            @endif
        </div>
    </header>
    <main class="wrap">
        @if(session('ok'))
            <div class="flash ok">{{ session('ok') }}</div>
        @endif
        @if($errors->any())
            <div class="flash err">{{ $errors->first() }}</div>
        @endif
        @yield('content')
    </main>
    @stack('scripts')
</body>
</html>
