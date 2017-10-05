from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormView, UpdateView

from cart.utils import get_cart
# from checkout.models.order import Order
from .forms import RegistrationForm, LoginForm
from .models import Profile


def profile_index(request):
    """
    Profile index view
    :param request:
    :return:
    """
    return render(request, "profile_index.html")


"""
    REGISTRATION AND AUTHENTICATION VIEWS
"""


class RegistrationFormView(FormView):
    """
    Registration View
    """
    template_name = "profile_register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy('products:index')

    def form_valid(self, form):
        self.profile = form.save()
        self.request.session['user_cart'] = self.request.session.session_key

        user = authenticate(
            email=self.profile.email,
            password=self.request.POST['password1']
        )

        messages.add_message(
            self.request, messages.SUCCESS,
            'You were successfully logged in.'
        )

        login(self.request, user)
        return super().form_valid(form)


class AuthenticationForm(FormView):
    """
    Authentication View
    """
    template_name = 'profile_login.html'
    form_class = LoginForm
    success_url = reverse_lazy('products:index')

    def form_valid(self, form):

        cart = get_cart(self.request, create=True)  # not important if using profile app directly
        user = authenticate(email=self.request.POST['email'], password=self.request.POST['password'])

        if user is not None and user.is_active:
            self.request.session['user_cart'] = self.request.session.session_key
            login(self.request, user)

            # not important if using profile app directly
            if cart is not None:
                cart.user = Profile.objects.get(id=user.id)
                cart.save()

            messages.add_message(self.request, messages.SUCCESS, 'You were successfully logged in.')

            return super().form_valid(form)

        else:
            response = super().form_invalid(form)
            messages.add_message(self.request, messages.WARNING, 'Wrong email or password. Please try again')
            return response


def logout_view(request):
    """
    Logout View
    """
    logout(request)
    return HttpResponseRedirect('/')


"""
    VIEWS FOR PROFILE DETAIL AND UPDATE
"""


class ProfileDetail(LoginRequiredMixin, DetailView):
    """
    Detail profile view for current user
    """
    template_name = "profile_detail.html"
    login_url = reverse_lazy('profiles:login')
    model = Profile

    def get_object(self, queryset=None):
        return Profile.objects.get(pk=self.request.user.pk)


class UpdateProfileForm(LoginRequiredMixin, UpdateView):
    """
    Profile Update View for current user
    """
    template_name = 'profile_update.html'
    form_class = RegistrationForm
    model = Profile
    success_url = reverse_lazy('homepage')
    login_url = reverse_lazy('profiles:login')

    def get_object(self, queryset=None):
        return Profile.objects.get(pk=self.request.user.pk)


"""
    USER ORDERS VIEWS (not important if using profile app directly)
"""


class ProfileOrdersView(LoginRequiredMixin, ListView):
    model = Profile #Order
    template_name = 'profile_orders.html'
    login_url = reverse_lazy('profiles:login')

    def get_context_data(self, **kwargs):
        context = super(ProfileOrdersView, self).get_context_data(**kwargs)
        # context['orders'] = Order.objects.filter(user=self.request.user.id)

        return context


class ProfileOrderDetailView(LoginRequiredMixin, DetailView):
    model = Profile #Order
    template_name = 'profile_order_detail.html'
    login_url = reverse_lazy('profiles:login')
