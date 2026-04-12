# tpe_app/views/auth_views.py
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Redirigir según el rol
            try:
                perfil = user.perfilusuario
                if perfil.rol == 'ADMINISTRADOR':
                    return redirect('admin_dashboard')
                elif perfil.rol == 'ABOGADO':
                    return redirect('abogado_dashboard')
                elif perfil.rol == 'BUSCADOR':
                    return redirect('buscador_dashboard')
                elif perfil.rol == 'ADMINISTRATIVO':
                    return redirect('auxiliar_dashboard')
            except:
                messages.error(request, 'Tu usuario no tiene un perfil asignado')
                logout(request)
                return redirect('login')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'tpe_app/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('login')