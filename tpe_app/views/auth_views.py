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
                if perfil.rol in ('MASTER', 'ADMINISTRADOR'):
                    return redirect('admin_dashboard')
                elif perfil.rol == 'AYUDANTE':
                    return redirect('ayudante_dashboard')
                elif perfil.rol in ('ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR', 'ABOGADO'):
                    return redirect('abogado_dashboard')
                elif perfil.rol in ('BUSCADOR', 'ABOG3_BUSCADOR'):
                    return redirect('buscador_dashboard')
                elif perfil.rol == 'ADMIN1_AGENDADOR':
                    return redirect('admin1_dashboard')
                elif perfil.rol == 'ADMIN2_ARCHIVO':
                    return redirect('admin2_dashboard')
                elif perfil.rol == 'ADMIN3_NOTIFICADOR':
                    return redirect('admin3_dashboard')
                elif perfil.rol == 'ADMINISTRATIVO':
                    return redirect('admin1_dashboard')
                elif perfil.rol == 'VOCAL_TPE':
                    return redirect('vocal_dashboard')
                elif perfil.rol == 'ASESOR_JURIDICO':
                    return redirect('buscador_dashboard')
                else:
                    messages.error(request, f'Rol no reconocido: {perfil.rol}')
                    logout(request)
                    return redirect('login')
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