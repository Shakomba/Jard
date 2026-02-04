import hashlib
import hmac
import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from io import BytesIO
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

import qrcode
from flask import Flask, render_template, redirect, url_for, request, flash, abort, send_file, session, has_request_context, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, inspect, text

from models import db, User, Household, Membership, Expense, ExpenseParticipant
from utils import generate_join_code, current_month_yyyy_mm, format_iqd, compute_net_balances, simplify_debts

TRANSLATIONS = {
    "en": {
        "app.name": "Daxli264",
        "menu.open": "Open menu",
        "menu.profile": "Profile",
        "menu.switch_theme": "Switch theme",
        "menu.switch_to_light": "Switch to light mode",
        "menu.switch_to_dark": "Switch to dark mode",
        "menu.language_to_en": "Switch to English",
        "menu.language_to_ku": "Switch to Kurdish",
        "menu.logout": "Logout",
        "menu.settings": "Settings",
        "nav.dashboard": "Dashboard",
        "nav.expenses": "Expenses",
        "nav.household": "Room",
        "nav.archive": "Archive",
        "common.confirm_action": "Are you sure",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.confirm": "Confirm",
        "common.you": "You",
        "common.admin": "Admin",
        "common.delete": "Delete",
        "common.add": "Add",
        "common.filter": "Filter",
        "common.or": "or",
        "common.password_placeholder": "Password",
        "common.logo": "Logo",
        "common.saving": "Saving...",
        "common.sending": "Sending",
        "login.title": "Login",
        "login.email_label": "Email",
        "login.password_label": "Password",
        "login.button": "Login",
        "login.create_account": "Create account",
        "login.forgot_password": "Forgot password",
        "login.email_placeholder": "you@example.com",
        "login.password_placeholder": "********",
        "login.email_required": "Email is required",
        "login.email_invalid": "Please enter a valid email address",
        "login.password_required": "Password is required",
        "login.logging_in": "Logging in...",
        "login.invalid_credentials": "Incorrect email or password",
        "login.login": "Login",
        "register.title": "Create account",
        "register.name_label": "Name",
        "register.email_label": "Email",
        "register.password_label": "Password",
        "register.confirm_password_label": "Confirm password",
        "register.password_help": "Use at least {min_len} characters, including a letter and a number",
        "register.password_rules_title": "Password requirements",
        "register.password_rule_length": "At least {min_len} characters",
        "register.password_rule_letter": "At least 1 letter (A–Z)",
        "register.password_rule_number": "At least 1 number (0–9)",
        "register.button": "Create account",
        "register.creating_account": "Creating account...",
        "register.have_account": "Already have an account",
        "register.name_placeholder": "Name",
        "register.email_placeholder": "you@example.com",
        "register.password_placeholder": "********",
        "register.email_step_title": "What's your email",
        "register.email_step_subtitle": "We'll use this to sign you in",
        "register.email_required": "Please enter your email",
        "register.email_invalid": "Please enter a valid email",
        "register.have_account_prefix": "Already have an account",
        "register.login_link": "Sign in",
        "register.password_step_title": "Create a password",
        "register.password_step_subtitle": "Choose a secure password",
        "register.password_required": "Please enter a password",
        "register.confirm_password_required": "Please confirm your password",
        "register.verify_step_title": "Check your email",
        "register.verify_step_subtitle": "Enter the 6-digit code we sent to",
        "register.start_over": "Start over",
        "register.change_email": "Change email",
        "register.profile_step_title": "Set up your profile",
        "register.profile_step_subtitle": "Tell us a bit about yourself",
        "register.upload_photo": "Add a photo",
        "register.name_required": "Please enter your name",
        "register.complete_button": "Complete setup",
        "verify.verifying": "Verifying...",
        "common.continue": "Continue",
        "common.back": "Back",
        "common.something_went_wrong": "Something went wrong. Please try again",
        "welcome.change_later_note": "You can change these later in settings",
        "reset.request_title": "Reset your password",
        "reset.request_help": "Enter your email and we'll send a reset link",
        "reset.email_label": "Email",
        "reset.email_placeholder": "you@example.com",
        "reset.request_button": "Send reset link",
        "reset.title": "Set a new password",
        "reset.password_label": "New password",
        "reset.confirm_password_label": "Confirm password",
        "reset.submit_button": "Update password",
        "email.greeting": "Hi",
        "email.there": "there",
        "email.button_not_working": "If the button does not work, copy and paste this link into your browser",
        "email.ignore_if_not_requested": "If you did not request a password reset, you can ignore this email",
        "email.ignore_if_not_requested_account": "If you did not create a Daxli264 account, you can ignore this email",
        "email.verify.subject": "Verify your Daxli264 email",
        "email.verify.code_is": "Your Daxli264 verification code is",
        "email.verify.code_help": "Enter this code in the app to verify your email. This code expires in {ttl_hours} hours",
        "email.reset.subject": "Reset your Daxli264 password",
        "email.reset.received_request": "We received a request to reset your Daxli264 password. This link expires in {ttl_minutes} minutes",
        "verify.title": "Verify your email",
        "verify.subtitle": "We sent a 6-digit code to {email}",
        "verify.help": "Enter the code below to verify your email",
        "verify.code_placeholder": "Enter code",
        "verify.resend_button": "Resend code",
        "verify.logout_button": "Log out",
        "verify.didnt_receive": "Didn't receive the code? Check spam or",
        "dashboard.welcome": "Welcome",
        "dashboard.they_owe_you": "They owe you",
        "dashboard.you_owe": "You owe",
        "dashboard.settled": "Settled",
        "dashboard.spending_by_person": "Spending by person",
        "dashboard.household_total": "Room total",
        "dashboard.suggested_payments": "Suggested payments",
        "dashboard.no_payments": "No payments needed",
        "dashboard.you_pay": "You pay",
        "dashboard.pays": "pays",
        "dashboard.members": "members",
        "dashboard.since": "Since",
        "dashboard.all_settled": "All balances are settled",
        "expenses.title": "Expenses",
        "expenses.add_title": "Add expense",
        "expenses.title_label": "Title",
        "expenses.title_placeholder": "e.g. Groceries",
        "expenses.amount_label": "Amount (IQD)",
        "expenses.amount_help": "Steps of 250 IQD",
        "expenses.date_label": "Date",
        "expenses.participants_label": "Participants",
        "expenses.add_button": "Add",
        "expenses.no_expenses": "No expenses yet",
        "expenses.delete_button": "Delete",
        "expenses.delete_confirm": "Delete this expense",
        "expenses.filtered_by": "Filtered by",
        "expenses.clear_filter": "Clear",
        "expenses.add_first": "Add your first expense to get started",
        "household.page_title": "Room",
        "household.edit_name": "Edit Name",
        "household.name_placeholder": "Room name",
        "household.remove_button": "Remove",
        "household.remove_confirm": "Remove {name} from the room",
        "household.join_code": "Join Code",
        "household.scan_to_join": "Scan to join",
        "household.qr_alt": "Join room QR code",
        "household.danger_zone": "Danger zone",
        "household.leave_title": "Leave room",
        "household.leave_help": "You can leave your current room and join another",
        "household.confirm_password": "Confirm password",
        "household.leave_button": "Leave Room",
        "household.leave_confirm": "Leave this room",
        "household.admin_transfer_warning": "As admin, ownership will transfer to the oldest member",
        "household.removing": "Removing...",
        "household.leaving": "Leaving...",
        "setup.create_title": "Create room",
        "setup.household_name_label": "Room name",
        "setup.household_name_placeholder": "Room",
        "setup.create_button": "Create",
        "setup.join_title": "Join room",
        "setup.join_code_label": "Join code",
        "setup.join_code_placeholder": "CODE",
        "setup.join_button": "Join",
        "setup.qr_title": "Join using a QR code",
        "setup.qr_description": "Scan live with your camera or select a QR image from your gallery",
        "setup.qr_scan_button": "Scan with camera",
        "setup.qr_select_button": "Select from gallery",
        "setup.qr_modal_title": "Scan QR",
        "setup.qr_modal_subtitle": "Join household",
        "setup.qr_modal_help": "Point your camera at the QR code",
        "setup.qr_close": "Close",
        "setup.qr_detected": "Detected code",
        "setup.qr_join_button": "Join Household",
        "setup.qr_scan_again": "Scan Again",
        "setup.qr_status.camera_not_supported": "Camera not supported in this browser",
        "setup.qr_status.scanner_unavailable": "Scanner not available. Reload and try again",
        "setup.qr_status.starting_camera": "Starting camera...",
        "setup.qr_status.camera_blocked": "Camera access blocked. Enable permissions and try again",
        "setup.qr_status.camera_failed": "Camera could not start. Try again",
        "setup.qr_status.invalid_code": "This QR code is not a household join code",
        "setup.qr_status.reading": "Reading QR...",
        "setup.qr_status.not_found": "No QR code found in that image. Try another one",
        "setup.qr_status.detected": "QR detected. Review to join",
        "setup.creating": "Creating...",
        "setup.joining": "Joining...",
        "archive.title": "Archive",
        "archive.sort_month": "By month",
        "archive.sort_settle": "By settle",
        "archive.sort_person": "By person",
        "archive.all_months": "All months",
        "archive.all_settles": "All settles",
        "archive.all_members": "All members",
        "archive.confirm_action": "Confirm action",
        "archive.settle_active": "Settle active expenses",
        "archive.settle_help": "This will archive all active expenses and reset balances for everyone",
        "archive.enter_password": "Enter your password",
        "archive.password_help": "We ask for your password to prevent accidental settles",
        "archive.confirm_settle": "Confirm settle",
        "archive.total_archived": "Total archived",
        "archive.expense_count": "expense",
        "archive.no_archived": "No archived expenses",
        "archive.danger_zone": "Danger zone",
        "archive.settle_button": "Settle",
        "archive.settle_label": "settle",
        "archive.archived_expenses": "Archived Expenses",
        "archive.items": "items",
        "archive.settled_appear_here": "Settled expenses will appear here",
        "profile.title": "Profile",
        "profile.subtitle": "Update your account details and preferences",
        "profile.email_verified": "Email verified",
        "profile.email_unverified": "Email not verified",
        "profile.resend_verification": "Resend verification email",
        "profile.upload_photo": "Upload photo",
        "profile.picture_alt": "Profile picture",
        "profile.password_heading": "Password",
        "profile.current_password": "Current password",
        "profile.current_password_placeholder": "Leave blank to keep",
        "profile.new_password": "New password",
        "profile.confirm_new_password": "Confirm new password",
        "profile.password_help": "Leave password fields empty to keep your current password",
        "profile.save_changes": "Save changes",
        "profile.danger_zone": "Danger zone",
        "profile.delete_title": "Delete account",
        "profile.delete_help": "This action cannot be undone",
        "profile.confirm_password": "Confirm password",
        "profile.delete_button": "Delete account",
        "profile.delete_confirm": "Delete your account? This cannot be undone",
        "profile.preferences": "Preferences",
        "profile.preferences_subtitle": "Customize your language and theme settings",
        "profile.language": "Language",
        "profile.theme": "Theme",
        "profile.dark": "Dark",
        "profile.light": "Light",
        "flash.fill_all_fields": "Please fill all fields",
        "flash.email_registered": "Email already registered. Please login",
        "flash.invalid_login": "Invalid email or password",
        "flash.already_in_household": "You are already in a household",
        "flash.invalid_join_code": "Invalid join code",
        "flash.joined_household": "Joined household {name}",
        "flash.name_empty": "Name cannot be empty",
        "flash.email_empty": "Email cannot be empty",
        "flash.email_in_use": "That email is already in use",
        "flash.enter_current_password": "Enter your current password to change it",
        "flash.current_password_incorrect": "Current password is incorrect",
        "flash.new_passwords_no_match": "New passwords do not match",
        "flash.passwords_no_match": "Passwords do not match",
        "flash.password_too_weak": "Password must be at least {min_len} characters and include a letter and a number",
        "flash.avatar_type_invalid": "Unsupported image type. Use PNG, JPG, or WEBP",
        "flash.profile_updated": "Profile updated",
        "flash.verification_email_sent": "Verification code sent. Please check your inbox",
        "flash.email_verified": "Your email has been verified",
        "flash.email_already_verified": "Your email is already verified",
        "flash.verification_code_invalid": "That verification code is incorrect",
        "flash.verification_code_expired": "That verification code has expired. Please request a new one",
        "flash.password_reset_sent": "If that email is registered, you'll receive a reset link shortly",
        "flash.password_reset_invalid": "That reset link is invalid or has expired",
        "flash.password_reset_success": "Your password has been updated. You can log in now",
        "flash.household_created": "Room created. Share the join code with your roommates",
        "flash.password_required": "Please enter your password to confirm",
        "flash.password_incorrect": "Incorrect password",
        "flash.admin_cant_leave": "Admins can't leave the room",
        "flash.settle_admin_only": "Only room admins can settle expenses",
        "flash.left_household": "You left the room",
        "flash.delete_account_blocked": "Remove other members or leave the room before deleting your account",
        "flash.account_deleted": "Account deleted",
        "flash.enter_join_code": "Please enter a join code",
        "flash.already_in_this_household": "You're already in this room",
        "flash.switched_household": "Switched to room {name}",
        "flash.admin_cant_switch": "Admins can't switch rooms while other members are in the room. Remove members first",
        "flash.use_leave_household": "Use 'Leave room' to remove yourself",
        "flash.cant_remove_admin": "You can't remove the room admin",
        "flash.user_not_member": "User is not a member of this room",
        "flash.member_removed": "Member removed",
        "flash.household_name_empty": "Room name cannot be empty",
        "flash.household_name_updated": "Room name updated",
        "flash.title_required": "Title is required",
        "flash.amount_positive": "Amount must be a positive integer (IQD)",
        "flash.select_participant": "Select at least one participant (who benefits from the expense)",
        "flash.invalid_participants": "Invalid participants selected",
        "flash.expense_added": "Expense added",
        "flash.only_payer_delete": "Only the payer can delete this expense",
        "flash.expense_deleted": "Expense deleted",
        "flash.nothing_to_settle": "Nothing to settle - no active expenses",
        "flash.settled_up": "Settled up! Archived expenses for {month}. Balances are now reset",
        "household.default_name": "My Household",
    },
    "ku": {
        "app.name": "Daxli264",
        "menu.open": "کردنەوەی لیست",
        "menu.profile": "پڕۆفایل",
        "menu.switch_theme": "گۆڕینی ڕووکار",
        "menu.switch_to_light": "دۆخی ڕووناک",
        "menu.switch_to_dark": "دۆخی تاریک",
        "menu.language_to_en": "English",
        "menu.language_to_ku": "کوردی",
        "menu.logout": "چوونەدەرەوە",
        "menu.settings": "ڕێکخستنەکان",
        "nav.dashboard": "سەرەکی",
        "nav.expenses": "خەرجییەکان",
        "nav.household": "ژوور",
        "nav.archive": "ئەرشیف",
        "common.confirm_action": "دڵنیایت؟",
        "common.save": "هەڵگرتن",
        "common.cancel": "پاشگەزبوونەوە",
        "common.confirm": "پشتڕاستکردنەوە",
        "common.you": "تۆ",
        "common.admin": "بەڕێوەبەر",
        "common.delete": "سڕینەوە",
        "common.add": "زیادکردن",
        "common.filter": "فلتەر",
        "common.or": "یان",
        "common.password_placeholder": "وشەی تێپەڕ",
        "common.logo": "لۆگۆ",
        "common.saving": "خەریکە هەڵدەگیرێت...",
        "common.sending": "ناردن...",
        "login.title": "چوونەژوورەوە",
        "login.email_label": "ئیمەیڵ",
        "login.password_label": "وشەی تێپەڕ",
        "login.button": "بچۆ ژوورەوە",
        "login.create_account": "هەژمار دروست بکە",
        "login.forgot_password": "وشەی تێپەڕت بیرچووە؟",
        "login.email_placeholder": "ناو@نموونە.com",
        "login.password_placeholder": "********",
        "login.email_required": "ئیمەیڵ پێویستە",
        "login.email_invalid": "تکایە ئیمەیڵێکی ڕاست بنووسە",
        "login.password_required": "وشەی تێپەڕ بنووسە",
        "login.logging_in": "خەریکە دەچیتە ژوورەوە...",
        "login.invalid_credentials": "ئیمەیڵ یان وشەی تێپەڕ هەڵەیە",
        "login.login": "چوونەژوورەوە",
        "register.title": "دروستکردنی هەژمار",
        "register.name_label": "ناوەکەت",
        "register.email_label": "ئیمەیڵ",
        "register.password_label": "وشەی تێپەڕ",
        "register.confirm_password_label": "دووبارەکردنەوەی وشەی تێپەڕ",
        "register.password_help": "دەبێت لانیکەم {min_len} نووسە بێت، پیت و ژمارەی تێدابێت",
        "register.password_rules_title": "مەرجەکانی وشەی تێپەڕ",
        "register.password_rule_length": "لانیکەم {min_len} نووسە",
        "register.password_rule_letter": "لانیکەم ١ پیت (A–Z)",
        "register.password_rule_number": "لانیکەم ١ ژمارە (0–9)",
        "register.button": "تۆمارکردن",
        "register.creating_account": "خەریکە هەژمار دروست دەکرێت...",
        "register.have_account": "هەژمارت هەیە؟",
        "register.name_placeholder": "ناوت لێرە بنووسە",
        "register.email_placeholder": "name@example.com",
        "register.password_placeholder": "********",
        "register.email_step_title": "ئیمەیڵەکەت بنووسە",
        "register.email_step_subtitle": "ئەم ئیمەیڵە بەکاردێت بۆ چوونەژوورەوە",
        "register.email_required": "تکایە ئیمەیڵەکەت بنووسە",
        "register.email_invalid": "ئیمەیڵەکە نادروستە",
        "register.have_account_prefix": "پێشتر هەژمارت دروستکردووە؟",
        "register.login_link": "بچۆ ژوورەوە",
        "register.password_step_title": "وشەی تێپەڕ دابنێ",
        "register.password_step_subtitle": "وشەیەکی بەهێز هەڵبژێرە",
        "register.password_required": "وشەی تێپەڕ پێویستە",
        "register.confirm_password_required": "تکایە وشەی تێپەڕ دووبارە بکەرەوە",
        "register.verify_step_title": "ئیمەیڵەکەت بپشکنە",
        "register.verify_step_subtitle": "کۆدێکی ٦ ژمارەییمان نارد بۆ",
        "register.start_over": "دەستپێکردنەوە",
        "register.change_email": "گۆڕینی ئیمەیڵ",
        "register.profile_step_title": "ڕێکخستنی پڕۆفایل",
        "register.profile_step_subtitle": "کەمێک زانیاری دەربارەی خۆت بنووسە",
        "register.upload_photo": "وێنەیەک دابنێ",
        "register.name_required": "تکایە ناوەکەت بنووسە",
        "register.complete_button": "تەواوکردنی ڕێکخستن",
        "verify.verifying": "خەریکە پشتڕاست دەکرێتەوە...",
        "common.continue": "بەردەوامبە",
        "common.back": "گەڕانەوە",
        "common.something_went_wrong": "هەڵەیەک ڕوویدا، تکایە دووبارە هەوڵبدەوە",
        "welcome.change_later_note": "دەتوانیت دواتر لە ڕێکخستنەکاندا ئەم زانیارییانە بگۆڕیت",
        "reset.request_title": "گۆڕینی وشەی تێپەڕ",
        "reset.request_help": "ئیمەیڵەکەت بنووسە بۆ ئەوەی لینکی گۆڕینت بۆ بنێرین",
        "reset.email_label": "ئیمەیڵ",
        "reset.email_placeholder": "you@example.com",
        "reset.request_button": "ناردنی لینک",
        "reset.title": "وشەی تێپەڕی نوێ",
        "reset.password_label": "وشەی تێپەڕی نوێ",
        "reset.confirm_password_label": "دووبارەکردنەوەی وشەی تێپەڕ",
        "reset.submit_button": "نوێکردنەوە",
        "email.greeting": "سڵاو",
        "email.there": "بەکارهێنەر",
        "email.button_not_working": "ئەگەر دوگمەکە کاری نەکرد، ئەم لینکە کۆپی بکە و لە وێبگەڕەکەتدا بیکەرەوە",
        "email.ignore_if_not_requested": "ئەگەر تۆ داوای گۆڕینی وشەی تێپەڕت نەکردووە، دەتوانیت ئەم ئیمەیڵە پشتگوێ بخەیت",
        "email.ignore_if_not_requested_account": "ئەگەر تۆ لە Daxli264 هەژمارت دروست نەکردووە، پشتگوێی بخە",
        "email.verify.subject": "پشتڕاستکردنەوەی ئیمەیڵ - Daxli264",
        "email.verify.code_is": "کۆدی پشتڕاستکردنەوەی تۆ:",
        "email.verify.code_help": "ئەم کۆدە لە ئەپەکەدا بەکاربهێنە. کۆدەکە تەنها بۆ {ttl_hours} کاتژمێر کار دەکات",
        "email.reset.subject": "گۆڕینی وشەی تێپەڕ - Daxli264",
        "email.reset.received_request": "داواکارییەکمان پێگەیشت بۆ گۆڕینی وشەی تێپەڕ. ئەم لینکە بۆ {ttl_minutes} خولەک کار دەکات",
        "verify.title": "پشتڕاستکردنەوە",
        "verify.subtitle": "کۆدێکی ٦ ژمارەییمان نارد بۆ {email}",
        "verify.help": "کۆدەکە لێرە بنووسە",
        "verify.code_placeholder": "کۆدەکە بنووسە",
        "verify.resend_button": "ناردنەوەی کۆد",
        "verify.logout_button": "چوونەدەرەوە",
        "verify.didnt_receive": "کۆدەکەت پێ نەگەیشتووە؟ سپام بپشکنە یان",
        "dashboard.welcome": "بەخێربێیت",
        "dashboard.they_owe_you": "قەرزداری تۆن",
        "dashboard.you_owe": "تۆ قەرزداریت",
        "dashboard.settled": "پاکتاوکراوە",
        "dashboard.spending_by_person": "خەرجییەکان بەپێی ئەندام",
        "dashboard.household_total": "کۆی گشتی خەرجی ژوور",
        "dashboard.suggested_payments": "پێشنیاری پارەدان",
        "dashboard.no_payments": "هیچ پارەدانێک پێویست نییە",
        "dashboard.you_pay": "تۆ دەدەیت بە",
        "dashboard.pays": "دەدات بە",
        "dashboard.members": "ئەندام",
        "dashboard.since": "لە ڕێکەوتی",
        "dashboard.all_settled": "هەموو حسابەکان پاکتاوکراون",
        "expenses.title": "خەرجییەکان",
        "expenses.add_title": "خەرجییەکی نوێ",
        "expenses.title_label": "بابەت",
        "expenses.title_placeholder": "بۆ نموونە: کڕینی سەوزە",
        "expenses.amount_label": "بڕ (بە دینار)",
        "expenses.amount_help": "جیاوازییەکە بە ٢٥٠ دینار دەبێت",
        "expenses.date_label": "ڕێکەوت",
        "expenses.participants_label": "بەشداربووان (کێ لێی سوودمەند بووە)",
        "expenses.add_button": "زیادکردن",
        "expenses.no_expenses": "هێشتا هیچ خەرجییەک تۆمار نەکراوە",
        "expenses.delete_button": "سڕینەوە",
        "expenses.delete_confirm": "دڵنیایت لە سڕینەوەی ئەم خەرجییە؟",
        "expenses.filtered_by": "فلتەرکراوە بەپێی:",
        "expenses.clear_filter": "لابردنی فلتەر",
        "expenses.add_first": "بۆ دەستپێکردن، یەکەم خەرجی زیاد بکە",
        "household.page_title": "ژوور",
        "household.edit_name": "گۆڕینی ناوی ژوور",
        "household.name_placeholder": "ناوی ژوور",
        "household.remove_button": "لابردن",
        "household.remove_confirm": "دڵنیایت لە لابردنی {name} لەم ژوورە؟",
        "household.join_code": "کۆدی ژوور",
        "household.scan_to_join": "سکان بکە بۆ هاتنەژوورەوە",
        "household.qr_alt": "QR کۆدی هاتنەژوورەوە",
        "household.danger_zone": "ناوچەی مەترسیدار",
        "household.leave_title": "جێهێشتنی ژوور",
        "household.leave_help": "دەتوانیت ئەم ژوورە جێبهێڵیت و بچیتە ژوورێکی تر",
        "household.confirm_password": "وشەی تێپەڕت بنووسە",
        "household.leave_button": "جێهێشتنی ژوور",
        "household.leave_confirm": "دڵنیایت لە جێهێشتنی ژوورەکە؟",
        "household.admin_transfer_warning": "وەک بەڕێوەبەر، ئەگەر بڕۆیت، بەڕێوەبەرایەتی دەدرێت بە کۆنترین ئەندام",
        "household.removing": "خەریکە لادەبرێت...",
        "household.leaving": "خەریکە جێدەهێڵرێت...",
        "setup.create_title": "دروستکردنی ژوور",
        "setup.household_name_label": "ناوی ژوور",
        "setup.household_name_placeholder": "ناوی ژوورەکە بنووسە",
        "setup.create_button": "دروستکردن",
        "setup.join_title": "چوونە ناو ژوور",
        "setup.join_code_label": "کۆدی هاتنەژوورەوە",
        "setup.join_code_placeholder": "کۆدەکە لێرە بنووسە",
        "setup.join_button": "بچۆ ناو ژوور",
        "setup.qr_title": "چوونەژوورەوە بە QR کۆد",
        "setup.qr_description": "سکان بکە یان وێنەی QR کۆدەکە لێرە دابنێ",
        "setup.qr_scan_button": "سکانکردن بە کامێرا",
        "setup.qr_select_button": "هەڵبژاردن لە گەلەری",
        "setup.qr_modal_title": "سکانکردنی کۆد",
        "setup.qr_modal_subtitle": "بۆ هاتنە ناو ژوور",
        "setup.qr_modal_help": "کامێراکەت ڕوو لە کۆدەکە بکە",
        "setup.qr_close": "داخستن",
        "setup.qr_detected": "کۆد دۆزرایەوە",
        "setup.qr_join_button": "بچۆ ناو ژوور",
        "setup.qr_scan_again": "دووبارە سکانکردنەوە",
        "setup.qr_status.camera_not_supported": "کامێرا لەم وێبگەڕەدا کار ناکات",
        "setup.qr_status.scanner_unavailable": "سکانەر بەردەست نییە، لاپەڕەکە نوێ بکەرەوە",
        "setup.qr_status.starting_camera": "خەریکە کامێرا دەکرێتەوە...",
        "setup.qr_status.camera_blocked": "ڕێگە بە کامێرا نەدراوە، تکایە مۆڵەت بدە",
        "setup.qr_status.camera_failed": "کامێرا نەکرایەوە، دووبارە هەوڵبدەوە",
        "setup.qr_status.invalid_code": "ئەم کۆدە هی هیچ ژوورێک نییە",
        "setup.qr_status.reading": "خوێندنەوەی کۆد...",
        "setup.qr_status.not_found": "هیچ کۆدێک لەم وێنەیەدا نەدۆزرایەوە",
        "setup.qr_status.detected": "کۆد دۆزرایەوە، پشتڕاستی بکەرەوە",
        "setup.creating": "خەریکە دروست دەکرێت...",
        "setup.joining": "خەریکە دەچیتە ناو ژوور...",
        "archive.title": "ئەرشیف",
        "archive.sort_month": "بەپێی مانگ",
        "archive.sort_settle": "بەپێی پاکتاوکردن",
        "archive.sort_person": "بەپێی ئەندام",
        "archive.all_months": "هەموو مانگەکان",
        "archive.all_settles": "هەموو پاکتاوەکان",
        "archive.all_members": "هەموو ئەندامەکان",
        "archive.confirm_action": "دڵنیابوونەوە",
        "archive.settle_active": "پاکتاوکردنی خەرجییەکان",
        "archive.settle_help": "بەمە هەموو خەرجییەکان ئەرشیف دەکرێن و حسابی هەمووان دەبێتەوە بە سفر",
        "archive.enter_password": "وشەی تێپەڕ بنووسە",
        "archive.password_help": "بۆ ئەوەی بە هەڵە پاکتاو نەکرێت، وشەی تێپەڕ پێویستە",
        "archive.confirm_settle": "پاکتاوکردن",
        "archive.total_archived": "کۆی گشتی ئەرشیفکراو",
        "archive.expense_count": "خەرجی",
        "archive.no_archived": "هیچ خەرجییەکی ئەرشیفکراو نییە",
        "archive.danger_zone": "ناوچەی مەترسیدار",
        "archive.settle_button": "پاکتاوکردنی ئێستا",
        "archive.settle_label": "پاکتاوکردن",
        "archive.archived_expenses": "خەرجییە ئەرشیفکراوەکان",
        "archive.items": "دانە",
        "archive.settled_appear_here": "خەرجییە پاکتاوکراوەکان لێرە دەردەکەون",
        "profile.title": "پڕۆفایل",
        "profile.subtitle": "زانیارییەکانت نوێ بکەرەوە",
        "profile.email_verified": "ئیمەیڵ پشتڕاستکراوەتەوە",
        "profile.email_unverified": "ئیمەیڵ پشتڕاست نەکراوەتەوە",
        "profile.resend_verification": "ناردنەوەی ئیمەیڵی پشتڕاستکردنەوە",
        "profile.upload_photo": "گۆڕینی وێنە",
        "profile.picture_alt": "وێنەی پڕۆفایل",
        "profile.password_heading": "گۆڕینی وشەی تێپەڕ",
        "profile.current_password": "وشەی تێپەڕی ئێستا",
        "profile.current_password_placeholder": "بەتاڵی بکە ئەگەر ناتەوێت بیگۆڕیت",
        "profile.new_password": "وشەی تێپەڕی نوێ",
        "profile.confirm_new_password": "دووبارەکردنەوەی وشەی تێپەڕ",
        "profile.password_help": "ئەگەر ناتەوێت وشەی تێپەڕ بگۆڕیت، ئەم خانانە پڕ مەکەرەوە",
        "profile.save_changes": "هەڵگرتنی گۆڕانکارییەکان",
        "profile.danger_zone": "ناوچەی مەترسیدار",
        "profile.delete_title": "سڕینەوەی هەژمار",
        "profile.delete_help": "ئەم کارە ناگەڕێتەوە و هەژمارەکەت بە یەکجاری دەسڕێتەوە",
        "profile.confirm_password": "وشەی تێپەڕ بنووسە",
        "profile.delete_button": "سڕینەوەی هەژمار",
        "profile.delete_confirm": "دڵنیایت لە سڕینەوەی هەژمارەکەت؟",
        "profile.preferences": "هەڵبژاردنەکان",
        "profile.preferences_subtitle": "زمان و ڕووکاری بەرنامە بگۆڕە",
        "profile.language": "زمان",
        "profile.theme": "ڕووکار",
        "profile.dark": "تاریک",
        "profile.light": "ڕووناک",
        "flash.fill_all_fields": "تکایە هەموو خانەکان پڕ بکەرەوە",
        "flash.email_registered": "ئەم ئیمەیڵە پێشتر تۆمارکراوە، تکایە بچۆ ژوورەوە",
        "flash.invalid_login": "ئیمەیڵ یان وشەی تێپەڕ هەڵەیە",
        "flash.already_in_household": "تۆ پێشتر لە ناو ژوورێکدایت",
        "flash.invalid_join_code": "کۆدەکە هەڵەیە، تکایە دڵنیابەرەوە",
        "flash.joined_household": "چوویتە ناو ژووری {name}",
        "flash.name_empty": "ناو پێویستە",
        "flash.email_empty": "ئیمەیڵ پێویستە",
        "flash.email_in_use": "ئەم ئیمەیڵە پێشتر بەکارهێنراوە",
        "flash.enter_current_password": "بۆ گۆڕین، دەبێت وشەی تێپەڕی ئێستات بنووسیت",
        "flash.current_password_incorrect": "وشەی تێپەڕی ئێستا هەڵەیە",
        "flash.new_passwords_no_match": "وشە تێپەڕە نوێیەکان وەک یەک نین",
        "flash.passwords_no_match": "وشە تێپەڕەکان وەک یەک نین",
        "flash.password_too_weak": "وشەی تێپەڕ دەبێت لانیکەم {min_len} نووسە بێت و پیت و ژمارەی تێدابێت",
        "flash.avatar_type_invalid": "جۆری وێنەکە گونجاو نییە، تەنها PNG, JPG یان WEBP",
        "flash.profile_updated": "زانیارییەکانت نوێکرانەوە",
        "flash.verification_email_sent": "کۆدەکە نێردرا، تکایە ئیمەیڵەکەت بپشکنە",
        "flash.email_verified": "ئیمەیڵەکەت پشتڕاستکرایەوە",
        "flash.email_already_verified": "ئیمەیڵەکەت پێشتر پشتڕاستکراوەتەوە",
        "flash.verification_code_invalid": "کۆدەکە هەڵەیە",
        "flash.verification_code_expired": "کاتی کۆدەکە بەسەرچووە، داوای یەکێکی نوێ بکە",
        "flash.password_reset_sent": "ئەگەر ئیمەیڵەکە تۆمار کرابێت، لینکی گۆڕینت بۆ دێت",
        "flash.password_reset_invalid": "لینکەکە هەڵەیە یان کاتی بەسەرچووە",
        "flash.password_reset_success": "وشەی تێپەڕ گۆڕدرا، ئێستا دەتوانیت بچیتە ژوورەوە",
        "flash.household_created": "ژوور دروستکرا، کۆدەکە بدە بە هاوڕێکانت",
        "flash.password_required": "بۆ دڵنیابوونەوە، وشەی تێپەڕ بنووسە",
        "flash.password_incorrect": "وشەی تێپەڕ هەڵەیە",
        "flash.admin_cant_leave": "بەڕێوەبەر ناتوانێت ژوور جێبهێڵێت",
        "flash.settle_admin_only": "تەنها بەڕێوەبەر دەتوانێت پاکتاو بکات",
        "flash.left_household": "ژوورەکەت جێهێشت",
        "flash.delete_account_blocked": "پێش سڕینەوە، دەبێت ژوورەکە جێبهێڵیت یان ئەندامەکان لادەیت",
        "flash.account_deleted": "هەژمارەکەت سڕایەوە",
        "flash.enter_join_code": "تکایە کۆدی هاتنەژوورەوە بنووسە",
        "flash.already_in_this_household": "تۆ پێشتر لەم ژوورەیت",
        "flash.switched_household": "گواسترایەوە بۆ ژووری {name}",
        "flash.admin_cant_switch": "بەڕێوەبەر ناتوانێت ژوور بگۆڕێت تا ئەندامی تر مابێت",
        "flash.use_leave_household": "بۆ دەرچوون 'جێهێشتنی ژوور' بەکاربهێنە",
        "flash.cant_remove_admin": "ناتوانیت بەڕێوەبەری ژوور لابەیت",
        "flash.user_not_member": "ئەم بەکارهێنەرە ئەندامی ئەم ژوورە نییە",
        "flash.member_removed": "ئەندامەکە لابرا",
        "flash.household_name_empty": "ناوی ژوور نابێت بەتاڵ بێت",
        "flash.household_name_updated": "ناوی ژوور گۆڕدرا",
        "flash.title_required": "ناونیشانی خەرجی بنووسە",
        "flash.amount_positive": "بڕی پارە دەبێت ژمارەیەکی دروست بێت",
        "flash.select_participant": "لانیکەم یەک کەس دیاری بکە کە خەرجییەکە دەگرێتەوە",
        "flash.invalid_participants": "بەشداربووی هەڵە دیاری کراوە",
        "flash.expense_added": "خەرجییەکە زیادکرا",
        "flash.only_payer_delete": "تەنها ئەو کەسەی پارەکەی داوە دەتوانێت بیسڕێتەوە",
        "flash.expense_deleted": "خەرجییەکە سڕایەوە",
        "flash.nothing_to_settle": "هیچ خەرجییەک نییە بۆ پاکتاوکردن",
        "flash.settled_up": "هەموو حسابەکان پاکتاوکران بۆ مانگی {month}",
        "household.default_name": "ژوورەکەی من",
    },
}

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///roommates.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = os.environ.get("REMEMBER_COOKIE_SAMESITE", "Lax")
    app.config["REMEMBER_COOKIE_SECURE"] = os.environ.get("REMEMBER_COOKIE_SECURE", "0") == "1"
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=int(os.environ.get("REMEMBER_COOKIE_DAYS", "30")))
    app.config["SECURITY_TOKEN_SECRET"] = os.environ.get("SECURITY_TOKEN_SECRET", app.config["SECRET_KEY"])
    app.config["PASSWORD_MIN_LENGTH"] = int(os.environ.get("PASSWORD_MIN_LENGTH", "8"))
    app.config["PASSWORD_REQUIRE_DIGIT"] = os.environ.get("PASSWORD_REQUIRE_DIGIT", "1") == "1"
    app.config["PASSWORD_REQUIRE_LETTER"] = os.environ.get("PASSWORD_REQUIRE_LETTER", "1") == "1"
    app.config["PASSWORD_REQUIRE_UPPER"] = os.environ.get("PASSWORD_REQUIRE_UPPER", "0") == "1"
    app.config["PASSWORD_REQUIRE_LOWER"] = os.environ.get("PASSWORD_REQUIRE_LOWER", "0") == "1"
    app.config["EMAIL_VERIFICATION_TTL_HOURS"] = int(os.environ.get("EMAIL_VERIFICATION_TTL_HOURS", "24"))
    app.config["PASSWORD_RESET_TTL_MINUTES"] = int(os.environ.get("PASSWORD_RESET_TTL_MINUTES", "60"))
    app.config["PASSWORD_RESET_COOLDOWN_MINUTES"] = max(
        0, int(os.environ.get("PASSWORD_RESET_COOLDOWN_MINUTES", "5"))
    )
    app.config["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "").strip()
    app.config["MAIL_HOST"] = os.environ.get("MAIL_HOST", "")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "1") == "1"
    app.config["MAIL_USE_SSL"] = os.environ.get("MAIL_USE_SSL", "0") == "1"
    app.config["MAIL_FROM"] = os.environ.get("MAIL_FROM", "no-reply@example.com")
    app.config["MAIL_TIMEOUT_SECONDS"] = max(1, int(os.environ.get("MAIL_TIMEOUT_SECONDS", "10")))

    db.init_app(app)

    def get_lang():
        # Check session first, then cookie, then default to 'en'
        lang = (session.get("lang") or request.cookies.get("lang") or "en").lower()
        return "ku" if lang == "ku" else "en"

    def t(key: str, **kwargs) -> str:
        lang = get_lang()
        text = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS.get("en", {}).get(key) or key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    app.jinja_env.globals["t"] = t
    app.jinja_env.globals["password_min_length"] = app.config["PASSWORD_MIN_LENGTH"]

    def build_external_url(endpoint: str, **values) -> str:
        base_url = app.config.get("APP_BASE_URL") or ""
        if base_url:
            path = url_for(endpoint, **values)
            return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        if has_request_context():
            return url_for(endpoint, _external=True, **values)
        return url_for(endpoint, **values)

    def is_safe_url(target: str) -> bool:
        if not target or not has_request_context():
            return False
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc

    def safe_next_url(target: str, fallback: str) -> str:
        return target if target and is_safe_url(target) else fallback

    def password_is_strong(password: str) -> bool:
        if not password or len(password) < app.config["PASSWORD_MIN_LENGTH"]:
            return False
        if app.config["PASSWORD_REQUIRE_DIGIT"] and not any(c.isdigit() for c in password):
            return False
        if app.config["PASSWORD_REQUIRE_LETTER"] and not any(c.isalpha() for c in password):
            return False
        if app.config["PASSWORD_REQUIRE_UPPER"] and not any(c.isupper() for c in password):
            return False
        if app.config["PASSWORD_REQUIRE_LOWER"] and not any(c.islower() for c in password):
            return False
        return True

    def token_hash(token: str) -> str:
        secret = app.config["SECURITY_TOKEN_SECRET"].encode("utf-8")
        return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()

    def issue_email_verification(user: User) -> str:
        # Generate a 6-digit verification code
        code = str(secrets.randbelow(900000) + 100000)  # 100000-999999
        user.email_verification_token_hash = token_hash(code)
        user.email_verification_sent_at = datetime.utcnow()
        user.email_verified = False
        return code

    def issue_password_reset(user: User) -> str:
        token = secrets.token_urlsafe(32)
        user.password_reset_token_hash = token_hash(token)
        user.password_reset_sent_at = datetime.utcnow()
        user.password_reset_expires_at = datetime.utcnow() + timedelta(
            minutes=app.config["PASSWORD_RESET_TTL_MINUTES"]
        )
        return token

    def password_reset_active(user: User) -> bool:
        if not user.password_reset_expires_at:
            return False
        return user.password_reset_expires_at >= datetime.utcnow()

    def password_reset_recent(user: User) -> bool:
        if not user.password_reset_sent_at:
            return False
        cooldown_minutes = app.config["PASSWORD_RESET_COOLDOWN_MINUTES"]
        if cooldown_minutes <= 0:
            return False
        return user.password_reset_sent_at + timedelta(minutes=cooldown_minutes) > datetime.utcnow()

    def email_enabled() -> bool:
        return bool(app.config["MAIL_HOST"])

    def send_email(to_email: str, subject: str, text_body: str, html_body=None) -> bool:
        if not email_enabled():
            # Print to terminal for development
            print("\n" + "=" * 60)
            print(f"EMAIL TO: {to_email}")
            print(f"SUBJECT: {subject}")
            print("-" * 60)
            print(text_body)
            print("=" * 60 + "\n")
            return True  # Return True so the flow continues
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr(("Daxli264", app.config["MAIL_FROM"]))
        msg["To"] = to_email
        msg.set_content(text_body or "")
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        host = app.config["MAIL_HOST"]
        port = app.config["MAIL_PORT"]
        username = app.config["MAIL_USERNAME"]
        password = app.config["MAIL_PASSWORD"]

        try:
            timeout = app.config["MAIL_TIMEOUT_SECONDS"]
            if app.config["MAIL_USE_SSL"]:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, context=context, timeout=timeout) as smtp:
                    smtp.ehlo()
                    if username:
                        smtp.login(username, password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                    smtp.ehlo()
                    if app.config["MAIL_USE_TLS"]:
                        context = ssl.create_default_context()
                        smtp.starttls(context=context)
                        smtp.ehlo()
                    if username:
                        smtp.login(username, password)
                    smtp.send_message(msg)
        except (smtplib.SMTPException, OSError):
            app.logger.exception("Email send failed: to=%s subject=%s", to_email, subject)
            return False
        return True

    def send_verification_email(user: User, code: str) -> bool:
        if not email_enabled():
            print(f"Email verification code for {user.email}: {code}")
            return False
        text_body = render_template(
            "emails/verify_email.txt",
            user=user,
            code=code,
            ttl_hours=app.config["EMAIL_VERIFICATION_TTL_HOURS"],
        )
        html_body = render_template(
            "emails/verify_email.html",
            user=user,
            code=code,
            ttl_hours=app.config["EMAIL_VERIFICATION_TTL_HOURS"],
        )
        return send_email(user.email, t("email.verify.subject"), text_body, html_body)

    def send_password_reset_email(user: User, token: str) -> bool:
        reset_url = build_external_url("reset_password", token=token)
        if not email_enabled():
            if app.debug or app.testing:
                app.logger.info("Password reset URL for %s: %s", user.email, reset_url)
                return True
            app.logger.warning("Email not configured; password reset email not sent for %s", user.email)
            return False
        text_body = render_template(
            "emails/reset_password.txt",
            user=user,
            reset_url=reset_url,
            ttl_minutes=app.config["PASSWORD_RESET_TTL_MINUTES"],
        )
        html_body = render_template(
            "emails/reset_password.html",
            user=user,
            reset_url=reset_url,
            ttl_minutes=app.config["PASSWORD_RESET_TTL_MINUTES"],
        )
        return send_email(user.email, t("email.reset.subject"), text_body, html_body)

    def ensure_user_schema() -> None:
        inspector = inspect(db.engine)
        if "user" not in inspector.get_table_names():
            return
        existing = {col["name"] for col in inspector.get_columns("user")}
        table = db.engine.dialect.identifier_preparer.quote("user")
        dialect = db.engine.dialect.name
        bool_default = "TRUE" if dialect in ("postgresql", "mysql") else "1"
        datetime_type = "TIMESTAMP" if dialect in ("postgresql", "mysql") else "DATETIME"
        updates = {
            "email_verified": f"BOOLEAN NOT NULL DEFAULT {bool_default}",
            "email_verification_token_hash": "VARCHAR(64)",
            "email_verification_sent_at": datetime_type,
            "password_reset_token_hash": "VARCHAR(64)",
            "password_reset_sent_at": datetime_type,
            "password_reset_expires_at": datetime_type,
        }
        with db.engine.begin() as conn:
            for col, sql_type in updates.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type}"))

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.session_protection = "strong"
    login_manager.init_app(app)

    with app.app_context():
        ensure_user_schema()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.template_filter("iqd")
    def _iqd(v):
        return format_iqd(v)

    def get_household_id_or_none():
        if not current_user.is_authenticated:
            return None
        m = Membership.query.filter_by(user_id=current_user.id).first()
        return m.household_id if m else None

    def require_household_id():
        hid = get_household_id_or_none()
        if not hid:
            return None
        return hid

    def household_members(household_id: int):
        rows = (
            db.session.query(User)
            .join(Membership, Membership.user_id == User.id)
            .filter(Membership.household_id == household_id)
            .order_by(User.name.asc())
            .all()
        )
        return rows

    def is_household_owner(household_id: int) -> bool:
        h = db.session.get(Household, household_id)
        if not h:
            return False
        # Best-effort backfill for older DBs
        if h.owner_id is None:
            first = Membership.query.filter_by(household_id=household_id).order_by(Membership.created_at.asc()).first()
            if first:
                h.owner_id = first.user_id
                db.session.commit()
        return (h.owner_id == current_user.id)

    AVATAR_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

    def avatar_dir():
        return os.path.join(app.root_path, "static", "uploads", "avatars")

    def avatar_path_for(user_id: int):
        for ext in AVATAR_EXTS:
            path = os.path.join(avatar_dir(), f"user_{user_id}{ext}")
            if os.path.exists(path):
                return path
        return None

    @app.context_processor
    def inject_household_state():
        return {
            "has_household": bool(get_household_id_or_none()),
            "lang": get_lang(),
            "password_min_length": app.config["PASSWORD_MIN_LENGTH"],
            "ep": request.endpoint or "",
        }

    def requires_email_verification() -> bool:
        return current_user.is_authenticated and current_user.email_verified is not True

    @app.before_request
    def enforce_email_verification():
        if not requires_email_verification():
            return None
        allowed = {
            "verify_required",
            "verify_email",
            "resend_verification",
            "logout",
            "static",
            "set_language",
        }
        if (request.endpoint or "") in allowed:
            return None
        return redirect(url_for("verify_required"))

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            hid = get_household_id_or_none()
            if not hid:
                return redirect(url_for("setup_household"))
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.post("/language")
    def set_language():
        lang = (request.form.get("lang") or "en").lower()
        if lang not in ("en", "ku"):
            lang = "en"
        session["lang"] = lang

        next_url = request.form.get("next") or request.referrer or url_for("dashboard")
        return redirect(safe_next_url(next_url, url_for("dashboard")))

    # ---------- Auth (Multi-step Registration) ----------

    # Step 1: Email + Password
    @app.get("/register")
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("register.html")

    @app.post("/register")
    def register_post():
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        next_raw = request.args.get("next") or request.form.get("next")
        next_url = safe_next_url(next_raw, "")

        if not email or not password or not confirm_password:
            flash(t("flash.fill_all_fields"), "error")
            return redirect(url_for("register", next=next_url) if next_url else url_for("register"))

        if password != confirm_password:
            flash(t("flash.passwords_no_match"), "error")
            return redirect(url_for("register", next=next_url) if next_url else url_for("register"))

        if User.query.filter_by(email=email).first():
            # Return JSON error for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "email_exists", "message": t("flash.email_registered")}), 400
            flash(t("flash.email_registered"), "error")
            return redirect(url_for("login", next=next_url) if next_url else url_for("login"))

        session["reg_email"] = email
        session["reg_password"] = password
        if next_url:
            session["reg_next"] = next_url

        # Generate and send verification code
        code = str(secrets.randbelow(900000) + 100000)
        session["reg_verify_code"] = code
        session["reg_verify_sent_at"] = datetime.utcnow().isoformat()

        # Send verification email
        try:
            html_body = render_template("emails/verify_email.html", user={"name": None}, code=code, ttl_hours=1)
            text_body = render_template("emails/verify_email.txt", user={"name": None}, code=code, ttl_hours=1)
            send_email(email, "Verify your Daxli264 email", text_body, html_body)
        except Exception as e:
            app.logger.error(f"Failed to send verification email: {e}")

        return redirect(url_for("register_verify"))

    # Step 2: Verification Code
    @app.get("/register/verify")
    def register_verify():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if "reg_email" not in session or "reg_password" not in session:
            return redirect(url_for("register"))
        return render_template("register_verify.html", email=session.get("reg_email"))

    @app.post("/register/verify")
    def register_verify_post():
        if "reg_email" not in session or "reg_password" not in session:
            return redirect(url_for("register"))

        code = request.form.get("code", "").strip()
        stored_code = session.get("reg_verify_code")

        if not code or code != stored_code:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": t("flash.verification_code_invalid")}), 400
            flash(t("flash.verification_code_invalid"), "error")
            return redirect(url_for("register_verify"))

        # Mark as verified and proceed to profile
        session["reg_verified"] = True

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "redirect": url_for("register_profile")})

        return redirect(url_for("register_profile"))

    @app.post("/register/resend-code")
    def register_resend_code():
        if "reg_email" not in session:
            return redirect(url_for("register"))

        code = str(secrets.randbelow(900000) + 100000)
        session["reg_verify_code"] = code
        session["reg_verify_sent_at"] = datetime.utcnow().isoformat()

        email = session["reg_email"]
        try:
            html_body = render_template("emails/verify_email.html", user={"name": None}, code=code, ttl_hours=1)
            text_body = render_template("emails/verify_email.txt", user={"name": None}, code=code, ttl_hours=1)
            send_email(email, "Verify your Daxli264 email", text_body, html_body)
            flash(t("flash.verification_email_sent"), "success")
        except Exception as e:
            app.logger.error(f"Failed to send verification email: {e}")
            flash(t("flash.email_send_failed"), "error")

        return redirect(url_for("register_verify"))

    # Step 3: Profile (Name + optional avatar)
    @app.get("/register/profile")
    def register_profile():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if "reg_email" not in session or "reg_password" not in session or not session.get("reg_verified"):
            return redirect(url_for("register"))
        return render_template("register_profile.html")

    @app.post("/register/profile")
    def register_profile_post():
        if "reg_email" not in session or "reg_password" not in session or not session.get("reg_verified"):
            return redirect(url_for("register"))

        name = request.form.get("name", "").strip()
        next_url = session.pop("reg_next", "")

        if not name:
            flash(t("flash.fill_all_fields"), "error")
            return redirect(url_for("register_profile"))

        # Create user
        email = session.pop("reg_email")
        password = session.pop("reg_password")
        session.pop("reg_verify_code", None)
        session.pop("reg_verify_sent_at", None)
        session.pop("reg_verified", None)

        u = User(
            name=name,
            email=email,
            password_hash=password,
            email_verified=True,
        )
        db.session.add(u)
        db.session.commit()

        # Handle avatar upload
        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            filename = secure_filename(avatar_file.filename)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext in AVATAR_EXTS:
                os.makedirs(avatar_dir(), exist_ok=True)
                dest = os.path.join(avatar_dir(), f"user_{u.id}{ext}")
                avatar_file.save(dest)

        session.permanent = True
        login_user(u, remember=True)

        if next_url:
            return redirect(next_url)
        return redirect(url_for("setup_household"))

    @app.get("/login")
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.post("/login")
    def login_post():
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_raw = request.args.get("next") or request.form.get("next")
        next_url = safe_next_url(next_raw, "")
        u = User.query.filter_by(email=email).first()
        if not u or u.password_hash != password:
            flash(t("flash.invalid_login"), "error")
            return redirect(url_for("login", next=next_url) if next_url else url_for("login"))
        session.permanent = True
        login_user(u, remember=True)
        if u.email_verified is not True:
            if next_url:
                session["post_verify_next"] = next_url
            return redirect(url_for("verify_required"))
        # Respect invite flows via ?next= or hidden form field
        if next_url:
            return redirect(next_url)

        hid = get_household_id_or_none()
        return redirect(url_for("setup_household" if not hid else "dashboard"))

    @app.get("/forgot-password")
    def forgot_password():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("forgot_password.html")

    @app.get("/verify-required")
    @login_required
    def verify_required():
        if current_user.email_verified:
            return redirect(url_for("dashboard"))
        return render_template("verify_required.html", title=t("verify.title"))

    @app.post("/forgot-password")
    def forgot_password_post():
        email = request.form.get("email", "").strip().lower()
        if email:
            u = User.query.filter_by(email=email).first()
            if u:
                if password_reset_recent(u) and password_reset_active(u):
                    pass
                elif not (email_enabled() or app.debug or app.testing):
                    app.logger.warning("Password reset requested but email is disabled for %s", u.email)
                else:
                    prev_reset = (
                        u.password_reset_token_hash,
                        u.password_reset_sent_at,
                        u.password_reset_expires_at,
                    )
                    reset_token = issue_password_reset(u)
                    db.session.commit()
                    if not send_password_reset_email(u, reset_token):
                        (
                            u.password_reset_token_hash,
                            u.password_reset_sent_at,
                            u.password_reset_expires_at,
                        ) = prev_reset
                        db.session.commit()
        flash(t("flash.password_reset_sent"), "success")
        return redirect(url_for("login"))

    @app.get("/reset-password/<token>")
    def reset_password(token: str):
        token_hash_value = token_hash(token)
        u = User.query.filter_by(password_reset_token_hash=token_hash_value).first()
        if not u or not u.password_reset_expires_at:
            flash(t("flash.password_reset_invalid"), "error")
            return redirect(url_for("login"))
        if u.password_reset_expires_at < datetime.utcnow():
            u.password_reset_token_hash = None
            u.password_reset_sent_at = None
            u.password_reset_expires_at = None
            db.session.commit()
            flash(t("flash.password_reset_invalid"), "error")
            return redirect(url_for("login"))
        return render_template("reset_password.html", token=token)

    @app.post("/reset-password/<token>")
    def reset_password_post(token: str):
        token_hash_value = token_hash(token)
        u = User.query.filter_by(password_reset_token_hash=token_hash_value).first()
        if not u or not u.password_reset_expires_at:
            flash(t("flash.password_reset_invalid"), "error")
            return redirect(url_for("login"))
        if u.password_reset_expires_at < datetime.utcnow():
            u.password_reset_token_hash = None
            u.password_reset_sent_at = None
            u.password_reset_expires_at = None
            db.session.commit()
            flash(t("flash.password_reset_invalid"), "error")
            return redirect(url_for("login"))

        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not new_password or not confirm_password:
            flash(t("flash.fill_all_fields"), "error")
            return redirect(url_for("reset_password", token=token))
        if new_password != confirm_password:
            flash(t("flash.passwords_no_match"), "error")
            return redirect(url_for("reset_password", token=token))

        u.password_hash = new_password
        u.password_reset_token_hash = None
        u.password_reset_sent_at = None
        u.password_reset_expires_at = None
        db.session.commit()
        flash(t("flash.password_reset_success"), "success")
        return redirect(url_for("login"))

    @app.post("/verify-code")
    @login_required
    def verify_code():
        code = request.form.get("code", "").strip()
        if not code:
            flash(t("flash.verification_code_invalid"), "error")
            return redirect(url_for("verify_required"))

        code_hash_value = token_hash(code)
        if current_user.email_verification_token_hash != code_hash_value:
            flash(t("flash.verification_code_invalid"), "error")
            return redirect(url_for("verify_required"))

        if not current_user.email_verification_sent_at:
            flash(t("flash.verification_code_invalid"), "error")
            return redirect(url_for("verify_required"))

        expires_at = current_user.email_verification_sent_at + timedelta(
            hours=app.config["EMAIL_VERIFICATION_TTL_HOURS"]
        )
        if expires_at < datetime.utcnow():
            current_user.email_verification_token_hash = None
            current_user.email_verification_sent_at = None
            db.session.commit()
            flash(t("flash.verification_code_expired"), "error")
            return redirect(url_for("verify_required"))

        current_user.email_verified = True
        current_user.email_verification_token_hash = None
        current_user.email_verification_sent_at = None
        db.session.commit()
        flash(t("flash.email_verified"), "success")
        next_url = safe_next_url(session.pop("post_verify_next", ""), "")
        if next_url:
            return redirect(next_url)
        return redirect(url_for("dashboard"))

    @app.get("/verify-email/<token>")
    def verify_email(token: str):
        token_hash_value = token_hash(token)
        u = User.query.filter_by(email_verification_token_hash=token_hash_value).first()
        if not u:
            flash(t("flash.verification_code_invalid"), "error")
            return redirect(url_for("login"))
        if not u.email_verification_sent_at:
            flash(t("flash.verification_code_invalid"), "error")
            return redirect(url_for("login"))

        expires_at = u.email_verification_sent_at + timedelta(
            hours=app.config["EMAIL_VERIFICATION_TTL_HOURS"]
        )
        if expires_at < datetime.utcnow():
            u.email_verification_token_hash = None
            u.email_verification_sent_at = None
            db.session.commit()
            flash(t("flash.verification_code_expired"), "error")
            return redirect(url_for("login"))

        u.email_verified = True
        u.email_verification_token_hash = None
        u.email_verification_sent_at = None
        db.session.commit()
        flash(t("flash.email_verified"), "success")
        if current_user.is_authenticated:
            next_url = safe_next_url(session.pop("post_verify_next", ""), "")
            if next_url:
                return redirect(next_url)
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.post("/profile/resend-verification")
    @login_required
    def resend_verification():
        if current_user.email_verified:
            flash(t("flash.email_already_verified"), "info")
            return redirect(url_for("profile"))
        verify_token = issue_email_verification(current_user)
        db.session.commit()
        send_verification_email(current_user, verify_token)
        flash(t("flash.verification_email_sent"), "success")
        return redirect(url_for("verify_required"))

    @app.get("/profile")
    @login_required
    def profile():
        return render_template("profile.html", title=t("profile.title"))

    # ---------- QR join (link target) ----------
    @app.get("/join/<code>")
    def qr_join(code: str):
        code = (code or "").strip().upper()
        if not code:
            return redirect(url_for("login"))

        if not current_user.is_authenticated:
            # send the user through auth, then back here
            return redirect(url_for("login", next=url_for("qr_join", code=code)))

        # Already in a household?
        hid = get_household_id_or_none()
        if hid:
            flash(t("flash.already_in_household"), "info")
            return redirect(url_for("dashboard"))

        h = Household.query.filter_by(join_code=code).first()
        if not h:
            flash(t("flash.invalid_join_code"), "error")
            return redirect(url_for("setup_household"))

        db.session.add(Membership(user_id=current_user.id, household_id=h.id))
        db.session.commit()
        flash(t("flash.joined_household", name=h.name), "success")
        return redirect(url_for("dashboard"))

    @app.route("/logout", methods=["GET", "POST"])
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.get("/avatar/<int:user_id>")
    def avatar(user_id: int):
        path = avatar_path_for(user_id)
        if path:
            return send_file(path, max_age=0)
        return send_file(os.path.join(app.root_path, "static", "avatar-placeholder.svg"), max_age=0)

    @app.post("/profile/update")
    @login_required
    def profile_update():
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        next_url = request.form.get("next", "")
        fallback = safe_next_url(request.referrer, url_for("dashboard"))
        redirect_to = safe_next_url(next_url, fallback)

        if not name:
            flash(t("flash.name_empty"), "error")
            return redirect(redirect_to)
        if not email:
            flash(t("flash.email_empty"), "error")
            return redirect(redirect_to)

        existing = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing:
            flash(t("flash.email_in_use"), "error")
            return redirect(redirect_to)

        if new_password or confirm_password:
            if not current_password:
                flash(t("flash.enter_current_password"), "error")
                return redirect(redirect_to)
            if current_user.password_hash != current_password:
                flash(t("flash.current_password_incorrect"), "error")
                return redirect(redirect_to)
            if new_password != confirm_password:
                flash(t("flash.new_passwords_no_match"), "error")
                return redirect(redirect_to)
            current_user.password_hash = new_password

        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            filename = secure_filename(avatar_file.filename)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext not in AVATAR_EXTS:
                flash(t("flash.avatar_type_invalid"), "error")
                return redirect(redirect_to)
            os.makedirs(avatar_dir(), exist_ok=True)
            for old_ext in AVATAR_EXTS:
                old_path = os.path.join(avatar_dir(), f"user_{current_user.id}{old_ext}")
                if os.path.exists(old_path):
                    os.remove(old_path)
            avatar_file.save(os.path.join(avatar_dir(), f"user_{current_user.id}{ext}"))

        email_changed = email != current_user.email
        current_user.name = name
        current_user.email = email
        verify_token = None
        if email_changed:
            verify_token = issue_email_verification(current_user)
        db.session.commit()
        if verify_token:
            send_verification_email(current_user, verify_token)
            flash(t("flash.verification_email_sent"), "success")
        flash(t("flash.profile_updated"), "success")
        return redirect(redirect_to)

    # ---------- Household setup ----------
    @app.get("/setup-household")
    @login_required
    def setup_household():
        hid = get_household_id_or_none()
        if hid:
            return redirect(url_for("household"))
        return render_template("setup_household.html")

    @app.post("/setup-household/create")
    @login_required
    def create_household():
        hid = get_household_id_or_none()
        if hid:
            return redirect(url_for("household"))

        name = request.form.get("household_name", "").strip() or t("household.default_name")

        # generate unique join code
        code = generate_join_code()
        while Household.query.filter_by(join_code=code).first():
            code = generate_join_code()

        h = Household(name=name, join_code=code, owner_id=current_user.id)
        db.session.add(h)
        db.session.commit()

        db.session.add(Membership(user_id=current_user.id, household_id=h.id))
        db.session.commit()

        flash(t("flash.household_created"), "success")
        # After creating a household during initial setup, send the user to the dashboard
        return redirect(url_for("dashboard"))

    @app.post("/setup-household/join")
    @login_required
    def join_household():
        hid = get_household_id_or_none()
        if hid:
            return redirect(url_for("household"))

        code = request.form.get("join_code", "").strip().upper()
        h = Household.query.filter_by(join_code=code).first()
        if not h:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": t("flash.invalid_join_code")}), 400
            flash(t("flash.invalid_join_code"), "error")
            return redirect(url_for("setup_household"))

        db.session.add(Membership(user_id=current_user.id, household_id=h.id))
        db.session.commit()
        flash(t("flash.joined_household", name=h.name), "success")
        return redirect(url_for("dashboard"))

    @app.get("/room")
    @login_required
    def household():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))
        h = db.session.get(Household, hid)

        # Best-effort backfill of owner_id for older DBs
        if h and h.owner_id is None:
            first = Membership.query.filter_by(household_id=hid).order_by(Membership.created_at.asc()).first()
            if first:
                h.owner_id = first.user_id
                db.session.commit()

        members = household_members(hid)
        owner_id = h.owner_id if h else None
        members.sort(key=lambda u: (u.id != owner_id, u.id != current_user.id, (u.name or "").lower()))

        is_owner = (h.owner_id == current_user.id)
        can_leave = True
        leave_block_reason = None

        return render_template(
            "household.html",
            household=h,
            members=members,
            is_owner=is_owner,
            owner_id=h.owner_id,
            can_leave=can_leave,
            leave_block_reason=leave_block_reason,
        )

    @app.get("/household")
    @login_required
    def household_legacy_redirect():
        return redirect(url_for("household"), code=301)

    @app.route("/household/leave", methods=["GET", "POST"])
    @login_required
    def leave_household():
        try:
            hid = require_household_id()
            if not hid:
                return redirect(url_for("setup_household"))

            h = db.session.get(Household, hid)
            if not h:
                abort(404)

            # Best-effort backfill owner_id
            if h.owner_id is None:
                first = Membership.query.filter_by(household_id=hid).order_by(Membership.created_at.asc()).first()
                if first:
                    h.owner_id = first.user_id
                    db.session.commit()

            # Check if this is the last member
            is_last_member = Membership.query.filter_by(household_id=hid).count() == 1
            
            # If admin is leaving, transfer ownership to next oldest member
            if h.owner_id == current_user.id and not is_last_member:
                next_member = Membership.query.filter(
                    Membership.household_id == hid,
                    Membership.user_id != current_user.id
                ).order_by(Membership.created_at.asc()).first()
                
                if next_member:
                    h.owner_id = next_member.user_id

            # Remove membership FIRST (before potentially deleting household)
            Membership.query.filter_by(user_id=current_user.id, household_id=hid).delete()
            
            # If this was the last member, delete the household
            if is_last_member:
                db.session.delete(h)

            db.session.commit()
            flash(t("flash.left_household"), "success")
            return redirect(url_for("setup_household"))
        except Exception as e:
            db.session.rollback()
            print(f"Error leaving household: {e}")
            import traceback
            traceback.print_exc()
            flash(t("common.something_went_wrong"), "error")
            return redirect(url_for("household"))

    @app.post("/account/delete")
    @login_required
    def delete_account():
        password = request.form.get("password", "")
        if not password or current_user.password_hash != password:
            flash(t("flash.password_incorrect"), "error")
            return redirect(request.referrer or url_for("dashboard"))

        user_id = current_user.id
        hid = get_household_id_or_none()
        if hid:
            h = db.session.get(Household, hid)
            member_count = Membership.query.filter_by(household_id=hid).count()
            if member_count > 1:
                flash(t("flash.delete_account_blocked"), "error")
                return redirect(url_for("household"))

            # Best-effort backfill owner_id
            if h and h.owner_id is None:
                first = Membership.query.filter_by(household_id=hid).order_by(Membership.created_at.asc()).first()
                if first:
                    h.owner_id = first.user_id
                    db.session.commit()

            Membership.query.filter_by(user_id=user_id).delete()
            if h:
                exp_ids = [e.id for e in Expense.query.filter_by(household_id=hid).all()]
                if exp_ids:
                    ExpenseParticipant.query.filter(ExpenseParticipant.expense_id.in_(exp_ids)).delete(synchronize_session=False)
                Expense.query.filter_by(household_id=hid).delete()
                db.session.delete(h)

        # Clean up any stray records tied to this user
        ExpenseParticipant.query.filter_by(user_id=user_id).delete()
        Expense.query.filter_by(payer_id=user_id).delete()
        Membership.query.filter_by(user_id=user_id).delete()

        # Remove avatar files
        for ext in AVATAR_EXTS:
            path = os.path.join(avatar_dir(), f"user_{user_id}{ext}")
            if os.path.exists(path):
                os.remove(path)

        logout_user()
        u = db.session.get(User, user_id)
        if u:
            db.session.delete(u)
        db.session.commit()
        flash(t("flash.account_deleted"), "success")
        return redirect(url_for("login"))

    
    @app.post("/household/switch")
    @login_required
    def switch_household():
        """Leave current household (if allowed) and join another by join_code."""
        current_hid = get_household_id_or_none()
        if not current_hid:
            return redirect(url_for("setup_household"))

        join_code = (request.form.get("join_code", "") or "").strip().upper()
        if not join_code:
            flash(t("flash.enter_join_code"), "error")
            return redirect(url_for("household"))

        target = Household.query.filter_by(join_code=join_code).first()
        if not target:
            flash(t("flash.invalid_join_code"), "error")
            return redirect(url_for("household"))

        if target.id == current_hid:
            flash(t("flash.already_in_this_household"), "info")
            return redirect(url_for("household"))

        current_house = db.session.get(Household, current_hid)
        if not current_house:
            # If membership exists but household is missing, clear membership and proceed.
            Membership.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
        else:
            # Best-effort backfill owner_id
            if current_house.owner_id is None:
                first = Membership.query.filter_by(household_id=current_hid).order_by(Membership.created_at.asc()).first()
                if first:
                    current_house.owner_id = first.user_id
                    db.session.commit()

            member_count = Membership.query.filter_by(household_id=current_hid).count()
            if current_house.owner_id == current_user.id and member_count > 1:
                flash(t("flash.admin_cant_switch"), "error")
                return redirect(url_for("household"))

            # Remove membership for this user (defensive: clear any stray memberships)
            Membership.query.filter_by(user_id=current_user.id).delete()

            # If this was the last member and also the owner, delete the household (and related data) to avoid orphaned data.
            if current_house.owner_id == current_user.id and member_count <= 1:
                exp_ids = [e.id for e in Expense.query.filter_by(household_id=current_hid).all()]
                if exp_ids:
                    ExpenseParticipant.query.filter(ExpenseParticipant.expense_id.in_(exp_ids)).delete(synchronize_session=False)
                Expense.query.filter_by(household_id=current_hid).delete()
                db.session.delete(current_house)

            db.session.commit()

        # Join target household
        db.session.add(Membership(user_id=current_user.id, household_id=target.id))
        db.session.commit()
        flash(t("flash.switched_household", name=target.name), "success")
        return redirect(url_for("dashboard"))

    @app.post("/household/remove/<int:user_id>")
    @login_required
    def remove_member(user_id: int):
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        h = db.session.get(Household, hid)
        if not h:
            abort(404)

        # Best-effort backfill owner_id
        if h.owner_id is None:
            first = Membership.query.filter_by(household_id=hid).order_by(Membership.created_at.asc()).first()
            if first:
                h.owner_id = first.user_id
                db.session.commit()

        if h.owner_id != current_user.id:
            abort(403)

        if user_id == current_user.id:
            flash(t("flash.use_leave_household"), "error")
            return redirect(url_for("household"))

        if user_id == h.owner_id:
            flash(t("flash.cant_remove_admin"), "error")
            return redirect(url_for("household"))

        m = Membership.query.filter_by(user_id=user_id, household_id=hid).first()
        if not m:
            flash(t("flash.user_not_member"), "error")
            return redirect(url_for("household"))

        Membership.query.filter_by(user_id=user_id, household_id=hid).delete()
        db.session.commit()
        flash(t("flash.member_removed"), "success")
        return redirect(url_for("household"))

    @app.post("/household/rename")
    @login_required
    def rename_household():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        h = db.session.get(Household, hid)
        if not h:
            abort(404)
        if h.owner_id != current_user.id:
            abort(403)

        new_name = request.form.get("name", "").strip()
        if not new_name:
            flash(t("flash.household_name_empty"), "error")
            return redirect(url_for("household"))

        h.name = new_name
        db.session.commit()
        flash(t("flash.household_name_updated"), "success")
        return redirect(url_for("household"))

    @app.get("/household/qr.png")
    @login_required
    def household_qr():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        h = db.session.get(Household, hid)
        if not h:
            abort(404)

        join_url = url_for("qr_join", code=h.join_code, _external=True)
        img = qrcode.make(join_url)
        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        return send_file(bio, mimetype="image/png", max_age=0)

    # ---------- Expenses ----------
    @app.get("/expenses")
    @login_required
    def expenses():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        members = household_members(hid)
        members.sort(key=lambda u: (u.id != current_user.id, (u.name or "").lower()))
        
        # Get filter and sort parameters
        filter_user = request.args.get("filter_user", "").strip()
        sort_by = request.args.get("sort", "date").strip()
        
        q = Expense.query.filter_by(household_id=hid, is_archived=False)
        
        # Apply user filter
        if filter_user:
            try:
                filter_user_id = int(filter_user)
                q = q.filter_by(payer_id=filter_user_id)
            except ValueError:
                filter_user = ""
        
        # Apply sorting
        if sort_by == "person":
            q = q.join(User, Expense.payer_id == User.id).order_by(User.name.asc(), Expense.expense_date.desc())
        else:
            sort_by = "date"
            q = q.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        
        exp = q.all()

        # payer names (include former members who have expenses)
        user_by_id = {u.id: u for u in members}
        payer_ids = {e.payer_id for e in exp}
        missing_ids = payer_ids - set(user_by_id.keys())
        if missing_ids:
            missing_users = User.query.filter(User.id.in_(missing_ids)).all()
            for u in missing_users:
                user_by_id[u.id] = u

        participants = ExpenseParticipant.query.join(
            Expense, ExpenseParticipant.expense_id == Expense.id
        ).filter(Expense.household_id == hid, Expense.is_archived == False).all()

        parts_map = {}
        for p in participants:
            parts_map.setdefault(p.expense_id, []).append(p.user_id)

        # Also include former members who are participants
        participant_ids = {p.user_id for p in participants}
        missing_participant_ids = participant_ids - set(user_by_id.keys())
        if missing_participant_ids:
            missing_users = User.query.filter(User.id.in_(missing_participant_ids)).all()
            for u in missing_users:
                user_by_id[u.id] = u

        today = datetime.now().strftime("%Y-%m-%d")
        return render_template(
            "expenses.html",
            members=members,
            expenses=exp,
            user_by_id=user_by_id,
            parts_map=parts_map,
            today=today,
            filter_user=filter_user,
            sort_by=sort_by,
        )

    @app.post("/expenses/add")
    @login_required
    def add_expense():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        title = request.form.get("title", "").strip()
        amount_str = request.form.get("amount_iqd", "").strip()
        expense_date = request.form.get("expense_date", "").strip()

        participant_ids = request.form.getlist("participants")  # list of strings
        try:
            participant_ids = [int(x) for x in participant_ids]
        except ValueError:
            participant_ids = []

        # basic validations
        if not title:
            flash(t("flash.title_required"), "error")
            return redirect(url_for("expenses"))

        try:
            amount_iqd = int(amount_str)
        except ValueError:
            amount_iqd = 0

        if amount_iqd <= 0:
            flash(t("flash.amount_positive"), "error")
            return redirect(url_for("expenses"))

        if not expense_date:
            expense_date = datetime.now().strftime("%Y-%m-%d")

        if len(participant_ids) == 0:
            flash(t("flash.select_participant"), "error")
            return redirect(url_for("expenses"))

        # verify participants belong to household
        members = household_members(hid)
        member_ids = {u.id for u in members}
        if not set(participant_ids).issubset(member_ids):
            flash(t("flash.invalid_participants"), "error")
            return redirect(url_for("expenses"))

        e = Expense(
            household_id=hid,
            payer_id=current_user.id,
            title=title,
            amount_iqd=amount_iqd,
            expense_date=expense_date,
            is_archived=False,
            archived_month=None,
        )
        db.session.add(e)
        db.session.commit()

        for uid in participant_ids:
            db.session.add(ExpenseParticipant(expense_id=e.id, user_id=uid))
        db.session.commit()

        flash(t("flash.expense_added"), "success")
        return redirect(url_for("expenses"))

    @app.post("/expenses/delete/<int:expense_id>")
    @login_required
    def delete_expense(expense_id: int):
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        e = db.session.get(Expense, expense_id)
        if not e or e.household_id != hid or e.is_archived:
            abort(404)

        # simple policy: only payer can delete
        if e.payer_id != current_user.id:
            flash(t("flash.only_payer_delete"), "error")
            return redirect(url_for("expenses"))

        ExpenseParticipant.query.filter_by(expense_id=e.id).delete()
        db.session.delete(e)
        db.session.commit()
        flash(t("flash.expense_deleted"), "success")
        return redirect(url_for("expenses"))

    # ---------- Dashboard (balances + simplified debts) ----------
    @app.get("/dashboard")
    @login_required
    def dashboard():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        members = household_members(hid)
        members.sort(key=lambda u: (u.id != current_user.id, (u.name or "").lower()))
        user_by_id = {u.id: u for u in members}

        active_expenses = Expense.query.filter_by(household_id=hid, is_archived=False).all()
        participants = ExpenseParticipant.query.join(
            Expense, ExpenseParticipant.expense_id == Expense.id
        ).filter(Expense.household_id == hid, Expense.is_archived == False).all()

        parts_map = {}
        for p in participants:
            parts_map.setdefault(p.expense_id, []).append(p.user_id)

        # Include former members who have expenses or are participants
        all_user_ids = {e.payer_id for e in active_expenses} | {p.user_id for p in participants}
        missing_ids = all_user_ids - set(user_by_id.keys())
        if missing_ids:
            missing_users = User.query.filter(User.id.in_(missing_ids)).all()
            for u in missing_users:
                user_by_id[u.id] = u

        net = compute_net_balances(members, active_expenses, parts_map)
        transfers = simplify_debts(net)

        i_owe = sum(amt for frm, to, amt in transfers if frm == current_user.id)
        owed_to_me = sum(amt for frm, to, amt in transfers if to == current_user.id)

        my_net = owed_to_me - i_owe  # positive => they owe me, negative => I owe
        my_total_spent = sum(e.amount_iqd for e in active_expenses if e.payer_id == current_user.id)
        household_total = sum(e.amount_iqd for e in active_expenses)

        # Spending by person (active only)
        spent_rows = (
            db.session.query(Expense.payer_id, func.coalesce(func.sum(Expense.amount_iqd), 0))
            .filter(Expense.household_id == hid, Expense.is_archived == False)
            .group_by(Expense.payer_id)
            .all()
        )
        spent_by_id = {pid: int(total or 0) for pid, total in spent_rows}
        spent_by_user = [(u, spent_by_id.get(u.id, 0)) for u in members]
        max_spent = max((amt for _u, amt in spent_by_user), default=0)

        # Calculate the earliest expense date, fallback to household period_start_date
        earliest_date = None
        if active_expenses:
            earliest_date = min(e.expense_date for e in active_expenses if e.expense_date)
        else:
            # No active expenses - use household's period start date (set after settle)
            household = db.session.get(Household, hid)
            if household and household.period_start_date:
                earliest_date = household.period_start_date

        month = current_month_yyyy_mm()
        return render_template(
            "dashboard.html",
            user_by_id=user_by_id,
            transfers=transfers,
            my_net=my_net,
            my_total_spent=my_total_spent,
            household_total=household_total,
            active_count=len(active_expenses),
            current_month=month,
            spent_by_user=spent_by_user,
            max_spent=max_spent,
            earliest_date=earliest_date,
        )

    # ---------- Settle (archive current expenses) ----------
    @app.post("/settle")
    @login_required
    def settle():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        if not is_household_owner(hid):
            flash(t("flash.settle_admin_only"), "error")
            return redirect(url_for("archive"))

        password = request.form.get("password", "")
        if not password or current_user.password_hash != password:
            flash(t("flash.password_incorrect"), "error")
            return redirect(url_for("archive"))

        month = current_month_yyyy_mm()
        settle_id = secrets.token_hex(8)
        settled_at = datetime.utcnow()
        active = Expense.query.filter_by(household_id=hid, is_archived=False).all()
        if not active:
            flash(t("flash.nothing_to_settle"), "info")
            return redirect(url_for("archive"))

        for e in active:
            e.is_archived = True
            e.archived_month = month
            e.archived_settle_id = settle_id
            e.archived_settled_at = settled_at

        # Update household period start date to today
        household = db.session.get(Household, hid)
        if household:
            household.period_start_date = settled_at.strftime("%Y-%m-%d")

        db.session.commit()

        flash(t("flash.settled_up", month=month), "success")
        return redirect(url_for("archive", sort="settle", settle=settle_id))

    # ---------- Archive ----------
    @app.get("/archive")
    @login_required
    def archive():
        hid = require_household_id()
        if not hid:
            return redirect(url_for("setup_household"))

        is_owner = is_household_owner(hid)
        lang = get_lang()
        sort = request.args.get("sort", "settle").strip().lower() or "settle"
        selected_month = request.args.get("month", "").strip()
        selected_settle = request.args.get("settle", "").strip()
        filter_person = request.args.get("person", "").strip()

        q = Expense.query.filter_by(household_id=hid, is_archived=True)

        # Apply person filter when sorting by person
        if sort == "person" and filter_person:
            try:
                person_id = int(filter_person)
                q = q.filter_by(payer_id=person_id)
            except ValueError:
                filter_person = ""

        if sort == "person":
            archived = q.join(User, Expense.payer_id == User.id).order_by(User.name.asc(), Expense.expense_date.desc()).all()
        else:
            sort = "settle"
            if selected_settle:
                q = q.filter_by(archived_settle_id=selected_settle)
            archived = q.order_by(Expense.archived_settled_at.desc().nullslast(), Expense.expense_date.desc()).all()

        # list available months
        months_rows = db.session.query(Expense.archived_month).filter(
            Expense.household_id == hid,
            Expense.is_archived == True,
            Expense.archived_month != None
        ).distinct().order_by(Expense.archived_month.desc()).all()
        months = [m[0] for m in months_rows if m[0]]

        # Available settle sessions (id + derived label)
        settle_rows = (
            db.session.query(
                Expense.archived_settle_id,
                func.min(Expense.expense_date),
                func.max(Expense.expense_date),
                func.max(Expense.archived_settled_at),
            )
            .filter(
                Expense.household_id == hid,
                Expense.is_archived == True,
                Expense.archived_settle_id != None,
            )
            .group_by(Expense.archived_settle_id)
            .order_by(func.max(Expense.archived_settled_at).desc())
            .all()
        )

        def _ordinal(n: int) -> str:
            if 10 <= (n % 100) <= 20:
                suf = "th"
            else:
                suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
            return f"{n}{suf}"

        def _fmt_settle_label(start_yyyy_mm_dd: str, end_yyyy_mm_dd: str) -> str:
            if lang == "ku":
                if start_yyyy_mm_dd == end_yyyy_mm_dd:
                    return f"{start_yyyy_mm_dd} {t('archive.settle_label')}"
                return f"{start_yyyy_mm_dd} - {end_yyyy_mm_dd} {t('archive.settle_label')}"
            # start/end are strings YYYY-MM-DD
            try:
                sdt = datetime.strptime(start_yyyy_mm_dd, "%Y-%m-%d")
                edt = datetime.strptime(end_yyyy_mm_dd, "%Y-%m-%d")
            except Exception:
                return t("archive.settle_label")

            if sdt.date() == edt.date():
                return f"{_ordinal(sdt.day)} {sdt.strftime('%b')} {t('archive.settle_label')}"
            # same month => "13th - 25th Dec settle"
            if sdt.year == edt.year and sdt.month == edt.month:
                return f"{_ordinal(sdt.day)} - {_ordinal(edt.day)} {sdt.strftime('%b')} {t('archive.settle_label')}"
            return f"{_ordinal(sdt.day)} {sdt.strftime('%b')} - {_ordinal(edt.day)} {edt.strftime('%b')} {t('archive.settle_label')}"

        settles = []
        for sid, smin, smax, sat in settle_rows:
            if not sid or not smin or not smax:
                continue
            settles.append({
                "id": sid,
                "label": _fmt_settle_label(smin, smax),
                "start": smin,
                "end": smax,
                "settled_at": sat,
            })

        members = household_members(hid)
        user_by_id = {u.id: u for u in members}

        shown_ids = [e.id for e in archived]
        participants = []
        if shown_ids:
            participants = ExpenseParticipant.query.filter(ExpenseParticipant.expense_id.in_(shown_ids)).all()

        parts_map = {}
        for p in participants:
            parts_map.setdefault(p.expense_id, []).append(p.user_id)

        # Include former members who have archived expenses or are participants
        all_user_ids = {e.payer_id for e in archived} | {p.user_id for p in participants}
        missing_ids = all_user_ids - set(user_by_id.keys())
        if missing_ids:
            missing_users = User.query.filter(User.id.in_(missing_ids)).all()
            for u in missing_users:
                user_by_id[u.id] = u

        total_iqd = sum(e.amount_iqd for e in archived)
        
        # Get settle info for selected settle
        selected_settle_info = None
        if selected_settle:
            for s in settles:
                if s["id"] == selected_settle:
                    selected_settle_info = s
                    break

        return render_template(
            "archive.html",
            archived=archived,
            months=months,
            settles=settles,
            settle_label_by_id={s["id"]: s["label"] for s in settles},
            sort=sort,
            selected_month=selected_month,
            selected_settle=selected_settle,
            selected_settle_info=selected_settle_info,
            filter_person=filter_person,
            total_iqd=total_iqd,
            user_by_id=user_by_id,
            parts_map=parts_map,
            is_owner=is_owner,
            members=members,
        )

    return app

app = create_app()

# Run migrations on startup
with app.app_context():
    db.create_all()
    # Add period_start_date column if missing (migration for existing DBs)
    try:
        db.session.execute(db.text("ALTER TABLE household ADD COLUMN period_start_date VARCHAR(10)"))
        db.session.commit()
    except Exception:
        db.session.rollback()  # Column likely already exists

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "init-db":
        init_db()
    else:
        app.run(debug=True)
