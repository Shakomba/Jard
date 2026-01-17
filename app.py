import hashlib
import hmac
import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from io import BytesIO
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

import qrcode
from flask import Flask, render_template, redirect, url_for, request, flash, abort, send_file, session, has_request_context
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, inspect, text

from models import db, User, Household, Membership, Expense, ExpenseParticipant
from utils import generate_join_code, current_month_yyyy_mm, format_iqd, compute_net_balances, simplify_debts

TRANSLATIONS = {
    "en": {
        "app.name": "Jard",
        "menu.open": "Open menu",
        "menu.profile": "Profile",
        "menu.switch_theme": "Switch theme",
        "menu.switch_to_light": "Switch to light mode",
        "menu.switch_to_dark": "Switch to dark mode",
        "menu.language_to_en": "Switch to English",
        "menu.language_to_ku": "Switch to Kurdish",
        "menu.logout": "Logout",
        "nav.dashboard": "Dashboard",
        "nav.expenses": "Expenses",
        "nav.household": "Household",
        "nav.archive": "Archive",
        "common.confirm_action": "Are you sure?",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.you": "You",
        "common.admin": "Admin",
        "common.delete": "Delete",
        "common.add": "Add",
        "common.filter": "Filter",
        "common.or": "or",
        "common.password_placeholder": "Password",
        "common.logo": "Logo",
        "login.title": "Login",
        "login.email_label": "Email",
        "login.password_label": "Password",
        "login.button": "Login",
        "login.create_account": "Create account",
        "login.forgot_password": "Forgot password?",
        "login.email_placeholder": "you@example.com",
        "login.password_placeholder": "********",
        "register.title": "Create account",
        "register.name_label": "Name",
        "register.email_label": "Email",
        "register.password_label": "Password",
        "register.confirm_password_label": "Confirm password",
        "register.password_help": "Use at least {min_len} characters, including a letter and a number.",
        "register.password_rules_title": "Password requirements:",
        "register.password_rule_length": "At least {min_len} characters",
        "register.password_rule_letter": "At least 1 letter (A–Z)",
        "register.password_rule_number": "At least 1 number (0–9)",
        "register.button": "Create account",
        "register.have_account": "Already have an account?",
        "register.name_placeholder": "Name",
        "register.email_placeholder": "you@example.com",
        "register.password_placeholder": "********",
        "reset.request_title": "Reset your password",
        "reset.request_help": "Enter your email and we'll send a reset link.",
        "reset.email_label": "Email",
        "reset.email_placeholder": "you@example.com",
        "reset.request_button": "Send reset link",
        "reset.title": "Set a new password",
        "reset.password_label": "New password",
        "reset.confirm_password_label": "Confirm password",
        "reset.submit_button": "Update password",
        "email.verify.subject": "Verify your Jard email",
        "email.reset.subject": "Reset your Jard password",
        "verify.title": "Verify your email",
        "verify.subtitle": "We sent a confirmation link to {email}. Please verify to continue.",
        "verify.help": "If you did not receive it, check spam or resend the email.",
        "verify.resend_button": "Resend verification email",
        "verify.logout_button": "Log out",
        "dashboard.welcome": "Welcome",
        "dashboard.they_owe_you": "They owe you",
        "dashboard.you_owe": "You owe",
        "dashboard.settled": "Settled",
        "dashboard.spending_by_person": "Spending by person",
        "dashboard.household_total": "Household total",
        "dashboard.suggested_payments": "Suggested payments",
        "dashboard.no_payments": "No payments needed.",
        "dashboard.you_pay": "You pay",
        "dashboard.pays": "pays",
        "expenses.title": "Expenses",
        "expenses.add_title": "Add expense",
        "expenses.title_label": "Title",
        "expenses.title_placeholder": "e.g. Groceries",
        "expenses.amount_label": "Amount (IQD)",
        "expenses.amount_help": "Steps of 250 IQD",
        "expenses.date_label": "Date",
        "expenses.participants_label": "Participants",
        "expenses.add_button": "Add",
        "expenses.no_expenses": "No expenses yet.",
        "expenses.delete_button": "Delete",
        "expenses.delete_confirm": "Delete this expense?",
        "household.edit_name": "Edit Name",
        "household.name_placeholder": "Household name",
        "household.remove_button": "Remove",
        "household.remove_confirm": "Remove {name} from the household?",
        "household.join_code": "Join Code",
        "household.scan_to_join": "Scan to join",
        "household.qr_alt": "Join household QR code",
        "household.danger_zone": "Danger zone",
        "household.leave_title": "Leave household",
        "household.leave_help": "You can leave your current household and join another.",
        "household.confirm_password": "Confirm password",
        "household.leave_button": "Leave Household",
        "household.leave_confirm": "Leave this household?",
        "setup.create_title": "Create household",
        "setup.household_name_label": "Household name",
        "setup.household_name_placeholder": "Household",
        "setup.create_button": "Create",
        "setup.join_title": "Join household",
        "setup.join_code_label": "Join code",
        "setup.join_code_placeholder": "CODE",
        "setup.join_button": "Join",
        "setup.qr_title": "Join using a QR code",
        "setup.qr_description": "Scan live with your camera or select a QR image from your gallery.",
        "setup.qr_scan_button": "Scan with camera",
        "setup.qr_select_button": "Select from gallery",
        "setup.qr_modal_title": "Scan QR",
        "setup.qr_modal_subtitle": "Join household",
        "setup.qr_modal_help": "Point your camera at the QR code.",
        "setup.qr_close": "Close",
        "setup.qr_detected": "Detected code",
        "setup.qr_join_button": "Join Household",
        "setup.qr_scan_again": "Scan Again",
        "setup.qr_status.camera_not_supported": "Camera not supported in this browser.",
        "setup.qr_status.scanner_unavailable": "Scanner not available. Reload and try again.",
        "setup.qr_status.starting_camera": "Starting camera...",
        "setup.qr_status.camera_blocked": "Camera access blocked. Enable permissions and try again.",
        "setup.qr_status.camera_failed": "Camera could not start. Try again.",
        "setup.qr_status.invalid_code": "This QR code is not a household join code.",
        "setup.qr_status.reading": "Reading QR...",
        "setup.qr_status.not_found": "No QR code found in that image. Try another one.",
        "setup.qr_status.detected": "QR detected. Review to join.",
        "archive.title": "Archive",
        "archive.sort_month": "By month",
        "archive.sort_settle": "By settle",
        "archive.all_months": "All months",
        "archive.all_settles": "All settles",
        "archive.confirm_action": "Confirm action",
        "archive.settle_active": "Settle active expenses",
        "archive.settle_help": "This will archive all active expenses and reset balances for everyone.",
        "archive.enter_password": "Enter your password",
        "archive.password_help": "We ask for your password to prevent accidental settles.",
        "archive.confirm_settle": "Confirm settle",
        "archive.total_archived": "Total archived",
        "archive.expense_count": "expense",
        "archive.no_archived": "No archived expenses.",
        "archive.danger_zone": "Danger zone",
        "archive.settle_button": "Settle",
        "archive.settle_label": "settle",
        "profile.title": "Profile",
        "profile.subtitle": "Update your account details and preferences.",
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
        "profile.password_help": "Leave password fields empty to keep your current password.",
        "profile.save_changes": "Save changes",
        "profile.danger_zone": "Danger zone",
        "profile.delete_title": "Delete account",
        "profile.delete_help": "This action cannot be undone.",
        "profile.confirm_password": "Confirm password",
        "profile.delete_button": "Delete account",
        "profile.delete_confirm": "Delete your account? This cannot be undone.",
        "flash.fill_all_fields": "Please fill all fields.",
        "flash.email_registered": "Email already registered. Please login.",
        "flash.invalid_login": "Invalid email or password.",
        "flash.already_in_household": "You are already in a household.",
        "flash.invalid_join_code": "Invalid join code.",
        "flash.joined_household": "Joined household: {name}",
        "flash.name_empty": "Name cannot be empty.",
        "flash.email_empty": "Email cannot be empty.",
        "flash.email_in_use": "That email is already in use.",
        "flash.enter_current_password": "Enter your current password to change it.",
        "flash.current_password_incorrect": "Current password is incorrect.",
        "flash.new_passwords_no_match": "New passwords do not match.",
        "flash.passwords_no_match": "Passwords do not match.",
        "flash.password_too_weak": "Password must be at least {min_len} characters and include a letter and a number.",
        "flash.avatar_type_invalid": "Unsupported image type. Use PNG, JPG, or WEBP.",
        "flash.profile_updated": "Profile updated.",
        "flash.verification_email_sent": "Verification email sent. Please check your inbox.",
        "flash.email_verified": "Your email has been verified.",
        "flash.email_already_verified": "Your email is already verified.",
        "flash.verification_link_invalid": "That verification link is invalid.",
        "flash.verification_link_expired": "That verification link has expired. Please request a new one.",
        "flash.password_reset_sent": "If that email is registered, you'll receive a reset link shortly.",
        "flash.password_reset_invalid": "That reset link is invalid or has expired.",
        "flash.password_reset_success": "Your password has been updated. You can log in now.",
        "flash.household_created": "Household created. Share the join code with your roommates.",
        "flash.password_required": "Please enter your password to confirm.",
        "flash.password_incorrect": "Incorrect password.",
        "flash.admin_cant_leave": "Admins can't leave the household.",
        "flash.settle_admin_only": "Only household admins can settle expenses.",
        "flash.left_household": "You left the household.",
        "flash.delete_account_blocked": "Remove other members or leave the household before deleting your account.",
        "flash.account_deleted": "Account deleted.",
        "flash.enter_join_code": "Please enter a join code.",
        "flash.already_in_this_household": "You're already in this household.",
        "flash.switched_household": "Switched to household: {name}",
        "flash.admin_cant_switch": "Admins can't switch households while other members are in the household. Remove members first.",
        "flash.use_leave_household": "Use 'Leave household' to remove yourself.",
        "flash.cant_remove_admin": "You can't remove the household admin.",
        "flash.user_not_member": "User is not a member of this household.",
        "flash.member_removed": "Member removed.",
        "flash.household_name_empty": "Household name cannot be empty.",
        "flash.household_name_updated": "Household name updated.",
        "flash.title_required": "Title is required.",
        "flash.amount_positive": "Amount must be a positive integer (IQD).",
        "flash.select_participant": "Select at least one participant (who benefits from the expense).",
        "flash.invalid_participants": "Invalid participants selected.",
        "flash.expense_added": "Expense added.",
        "flash.only_payer_delete": "Only the payer can delete this expense.",
        "flash.expense_deleted": "Expense deleted.",
        "flash.nothing_to_settle": "Nothing to settle - no active expenses.",
        "flash.settled_up": "Settled up! Archived expenses for {month}. Balances are now reset.",
        "household.default_name": "My Household",
    },
    "ku": {
        "app.name": "Jard",
        "menu.open": "کردنەوەی مێنوو",
        "menu.profile": "پرۆفایل",
        "menu.switch_theme": "گۆڕینی ڕووکار",
        "menu.switch_to_light": "گۆڕین بۆ مۆدی ڕووناک",
        "menu.switch_to_dark": "گۆڕین بۆ مۆدی تاریک",
        "menu.language_to_en": "گۆڕین بۆ ئینگلیزی",
        "menu.language_to_ku": "گۆڕین بۆ کوردی",
        "menu.logout": "دەرچوون",
        "nav.dashboard": "داشبۆرد",
        "nav.expenses": "خەرجییەکان",
        "nav.household": "ماڵەوە",
        "nav.archive": "ئەرشیف",
        "common.confirm_action": "دڵنیایت؟",
        "common.save": "پاشەکەوتکردن",
        "common.cancel": "هەڵوەشاندنەوە",
        "common.you": "تۆ",
        "common.admin": "بەڕێوەبەر",
        "common.delete": "سڕینەوە",
        "common.add": "زیادکردن",
        "common.filter": "پاڵاوتن",
        "common.or": "یان",
        "common.password_placeholder": "وشەی نهێنی",
        "common.logo": "لۆگۆ",
        "login.title": "چوونەژوورەوە",
        "login.email_label": "ئیمەیڵ",
        "login.password_label": "وشەی نهێنی",
        "login.button": "چوونەژوورەوە",
        "login.create_account": "دروستکردنی هەژمار",
        "login.forgot_password": "وشەی نهێنیت لەبیرچووە؟",
        "login.email_placeholder": "you@example.com",
        "login.password_placeholder": "********",
        "register.title": "دروستکردنی هەژمار",
        "register.name_label": "ناو",
        "register.email_label": "ئیمەیڵ",
        "register.password_label": "وشەی نهێنی",
        "register.confirm_password_label": "دووبارەکردنەوەی وشەی نهێنی",
        "register.password_help": "بەلایەنی کەم {min_len} پیت بەکاربهێنە، پیت و ژمارەی تێدابێت.",
        "register.button": "دروستکردنی هەژمار",
        "register.have_account": "پێشتر هەژمارت هەیە؟",
        "register.name_placeholder": "ناوت لێرە بنووسە",
        "register.email_placeholder": "you@example.com",
        "register.password_placeholder": "********",
        "reset.request_title": "گۆڕینی وشەی نهێنی",
        "reset.request_help": "ئیمەیڵەکەت بنووسە بۆ ناردنی لینکی گۆڕینی وشەی نهێنی.",
        "reset.email_label": "ئیمەیڵ",
        "reset.email_placeholder": "you@example.com",
        "reset.request_button": "ناردنی لینکی گۆڕین",
        "reset.title": "وشەی نهێنی نوێ بنووسە",
        "reset.password_label": "وشەی نهێنی نوێ",
        "reset.confirm_password_label": "دووبارەکردنەوەی وشەی نهێنی",
        "reset.submit_button": "نوێکردنەوەی وشەی نهێنی",
        "email.verify.subject": "پشتڕاستکردنەوەی ئیمەیڵی Jard",
        "email.reset.subject": "گۆڕینی وشەی نهێنی Jard",
        "verify.title": "Verify your email",
        "verify.subtitle": "We sent a confirmation link to {email}. Please verify to continue.",
        "verify.help": "If you did not receive it, check spam or resend the email.",
        "verify.resend_button": "Resend verification email",
        "verify.logout_button": "Log out",
        "dashboard.welcome": "بەخێربێیت",
        "dashboard.they_owe_you": "قەرزداری تۆن",
        "dashboard.you_owe": "تۆ قەرزداریت",
        "dashboard.settled": "یەکسانکراوەتەوە",
        "dashboard.spending_by_person": "خەرجی بەپێی کەسەکان",
        "dashboard.household_total": "کۆی گشتی ماڵەوە",
        "dashboard.suggested_payments": "پارەدانە پێشنیارکراوەکان",
        "dashboard.no_payments": "هیچ پارەدانێک پێویست نییە.",
        "dashboard.you_pay": "تۆ دەدەیت بە",
        "dashboard.pays": "دەدات بە",
        "expenses.title": "خەرجییەکان",
        "expenses.add_title": "زیادکردنی خەرجی",
        "expenses.title_label": "ناونیشان",
        "expenses.title_placeholder": "بۆ نموونە: سەوزە و میوە",
        "expenses.amount_label": "بڕ (بە دینار)",
        "expenses.amount_help": "بە هەنگاوی ٢٥٠ دینار",
        "expenses.date_label": "ڕێکەوت",
        "expenses.participants_label": "بەشداربووەکان (ئەوانەی تێیدا هاوبەشن)",
        "expenses.add_button": "زیادکردن",
        "expenses.no_expenses": "هێشتا هیچ خەرجییەک نییە.",
        "expenses.delete_button": "سڕینەوە",
        "expenses.delete_confirm": "دڵنیایت لە سڕینەوەی ئەم خەرجییە؟",
        "household.edit_name": "دەستکاری ناو",
        "household.name_placeholder": "ناوی ماڵەوە",
        "household.remove_button": "لابردن",
        "household.remove_confirm": "دڵنیایت لە لابردنی {name} لە ماڵەوە؟",
        "household.join_code": "کۆدی بەشداریکردن",
        "household.scan_to_join": "سکان بکە بۆ بەشداریکردن",
        "household.qr_alt": "کۆدی QR بۆ بەشداریکردن",
        "household.danger_zone": "ناوچەی مەترسی",
        "household.leave_title": "جێهێشتنی ماڵەوە",
        "household.leave_help": "دەتوانیت ئەم ماڵەوەیە جێبهێڵیت و بەشداری ماڵێکی تر بکەیت.",
        "household.confirm_password": "وشەی نهێنی بنووسە بۆ دڵنیابوونەوە",
        "household.leave_button": "جێهێشتنی ماڵەوە",
        "household.leave_confirm": "دڵنیایت لە جێهێشتنی ئەم ماڵەوەیە؟",
        "setup.create_title": "دروستکردنی ماڵەوە",
        "setup.household_name_label": "ناوی ماڵەوە",
        "setup.household_name_placeholder": "ماڵەکەم",
        "setup.create_button": "دروستکردن",
        "setup.join_title": "بەشداریکردن لە ماڵەوە",
        "setup.join_code_label": "کۆدی بەشداریکردن",
        "setup.join_code_placeholder": "لێرە بنووسە",
        "setup.join_button": "بەشداریکردن",
        "setup.qr_title": "بەشداریکردن بە کۆدی QR",
        "setup.qr_description": "سکان بکە بە کامێرا یان وێنەیەک لە گەلەری هەڵبژێرە.",
        "setup.qr_scan_button": "سکانکردن بە کامێرا",
        "setup.qr_select_button": "هەڵبژاردن لە گەلەری",
        "setup.qr_modal_title": "سکانکردنی کۆد",
        "setup.qr_modal_subtitle": "بەشداریکردن لە ماڵەوە",
        "setup.qr_modal_help": "کامێراکەت ڕوو لە کۆدەکە بگرە.",
        "setup.qr_close": "داخستن",
        "setup.qr_detected": "کۆدەکە دۆزرایەوە",
        "setup.qr_join_button": "بەشداریکردن لە ماڵەوە",
        "setup.qr_scan_again": "دووبارە سکانکردنەوە",
        "setup.qr_status.camera_not_supported": "کامێرا لەم وێبگەڕەدا پشتگیری ناکرێت.",
        "setup.qr_status.scanner_unavailable": "سکانەر بەردەست نییە. لاپەڕەکە نوێ بکەرەوە.",
        "setup.qr_status.starting_camera": "کامێرا دەستپێدەکات...",
        "setup.qr_status.camera_blocked": "ڕێگری لە کامێرا کراوە. مۆڵەت بدە و هەوڵ بدە.",
        "setup.qr_status.camera_failed": "کامێرا کاری نەکرد. دووبارە هەوڵ بدە.",
        "setup.qr_status.invalid_code": "ئەم کۆدە کۆدی بەشداریکردنی ماڵەوە نییە.",
        "setup.qr_status.reading": "خوێندنەوەی کۆد...",
        "setup.qr_status.not_found": "هیچ کۆدێک لەم وێنەیەدا نەدۆزرایەوە.",
        "setup.qr_status.detected": "کۆد دۆزرایەوە. پێداچوونەوە بکە.",
        "archive.title": "ئەرشیف",
        "archive.sort_month": "بەپێی مانگ",
        "archive.sort_settle": "بەپێی کاتی یەکسانکردنەوە",
        "archive.all_months": "هەموو مانگەکان",
        "archive.all_settles": "هەموو یەکسانکردنەوەکان",
        "archive.confirm_action": "دڵنیابوونەوە",
        "archive.settle_active": "یەکسانکردنەوەی خەرجییە چالاکەکان",
        "archive.settle_help": "ئەمە هەموو خەرجییەکان ئەرشیف دەکات و باڵانسی هەمووان سفر دەکاتەوە.",
        "archive.enter_password": "وشەی نهێنی بنووسە",
        "archive.password_help": "بۆ ڕێگریکردن لە یەکسانکردنەوەی هەڵە، وشەی نهێنیت پێویستە.",
        "archive.confirm_settle": "دڵنیاییت لە یەکسانکردنەوە",
        "archive.total_archived": "کۆی گشتی ئەرشیفکراو",
        "archive.expense_count": "خەرجی",
        "archive.no_archived": "هیچ خەرجییەکی ئەرشیفکراو نییە.",
        "archive.danger_zone": "ناوچەی مەترسی",
        "archive.settle_button": "یەکسانکردنەوە",
        "archive.settle_label": "یەکسانکردنەوە",
        "profile.title": "پرۆفایل",
        "profile.subtitle": "زانیاری و هەڵبژاردەکانی هەژمارەکەت نوێ بکەرەوە.",
        "profile.email_verified": "ئیمەیڵ پشتڕاستکراوەتەوە",
        "profile.email_unverified": "ئیمەیڵ پشتڕاست نەکراوەتەوە",
        "profile.resend_verification": "دووبارە ناردنی ئیمەیڵی پشتڕاستکردنەوە",
        "profile.upload_photo": "بارکردنی وێنە",
        "profile.picture_alt": "وێنەی پرۆفایل",
        "profile.password_heading": "گۆڕینی وشەی نهێنی",
        "profile.current_password": "وشەی نهێنی ئێستا",
        "profile.current_password_placeholder": "بەتاڵی بهێڵەرەوە بۆ نەگۆڕین",
        "profile.new_password": "وشەی نهێنی نوێ",
        "profile.confirm_new_password": "دووبارەکردنەوەی وشەی نهێنی نوێ",
        "profile.password_help": "ئەگەر خانەکان بەتاڵ بن، وشەی نهێنییەکەت ناگۆڕێت.",
        "profile.save_changes": "پاشەکەوتکردنی گۆڕانکارییەکان",
        "profile.danger_zone": "ناوچەی مەترسی",
        "profile.delete_title": "سڕینەوەی هەژمار",
        "profile.delete_help": "ئەم کارە ناگەڕێتەوە و هەژمارەکەت بەتەواوی دەسڕێتەوە.",
        "profile.confirm_password": "وشەی نهێنی بنووسە بۆ دڵنیابوونەوە",
        "profile.delete_button": "سڕینەوەی هەژمار",
        "profile.delete_confirm": "دڵنیایت لە سڕینەوەی هەژمارەکەت؟ ئەم کارە ناگەڕێتەوە.",
        "flash.fill_all_fields": "تکایە هەموو خانەکان پڕ بکەرەوە.",
        "flash.email_registered": "ئەم ئیمەیڵە پێشتر تۆمارکراوە. تکایە بچۆ ژوورەوە.",
        "flash.invalid_login": "ئیمەیڵ یان وشەی نهێنی هەڵەیە.",
        "flash.already_in_household": "تۆ لە ئێستادا لە ناو ماڵەوەیەکی.",
        "flash.invalid_join_code": "کۆدی بەشداریکردن هەڵەیە.",
        "flash.joined_household": "بەشداریت کرد لە ماڵەوەی: {name}",
        "flash.name_empty": "ناو نابێت بەتاڵ بێت.",
        "flash.email_empty": "ئیمەیڵ نابێت بەتاڵ بێت.",
        "flash.email_in_use": "ئەم ئیمەیڵە پێشتر بەکارهێنراوە.",
        "flash.enter_current_password": "تکایە وشەی نهێنی ئێستات بنووسە بۆ گۆڕینی.",
        "flash.current_password_incorrect": "وشەی نهێنی ئێستا هەڵەیە.",
        "flash.new_passwords_no_match": "وشە نهێنییە نوێیەکان وەک یەک نین.",
        "flash.passwords_no_match": "وشە نهێنییەکان وەک یەک نین.",
        "flash.password_too_weak": "وشەی نهێنی دەبێت لانیکەم {min_len} پیت بێت و پیت و ژمارەی تێدابێت.",
        "flash.avatar_type_invalid": "جۆری وێنەکە گونجاو نییە. تەنها PNG، JPG یان WEBP.",
        "flash.profile_updated": "پرۆفایلەکەت نوێکرایەوە.",
        "flash.verification_email_sent": "ئیمەیڵی پشتڕاستکردنەوە نێردرا. تکایە سەیری ئیمەیڵەکەت بکە.",
        "flash.email_verified": "ئیمەیڵەکەت بەسەرکەوتوویی پشتڕاستکرایەوە.",
        "flash.email_already_verified": "ئیمەیڵەکەت پێشتر پشتڕاستکراوەتەوە.",
        "flash.verification_link_invalid": "ئەم لێنکە هەڵەیە یان کار ناکات.",
        "flash.verification_link_expired": "کاتی لێنکەکە بەسەرچووە. تکایە داوای یەکێکی نوێ بکە.",
        "flash.password_reset_sent": "ئەگەر ئیمەیڵەکە تۆمارکرابێت، لێنکی گۆڕینی وشەی نهێنیت بۆ دەنێردرێت.",
        "flash.password_reset_invalid": "لێنکەکە هەڵەیە یان کاتی بەسەرچووە.",
        "flash.password_reset_success": "وشەی نهێنی نوێکراوە. ئێستا دەتوانیت بچیتە ژوورەوە.",
        "flash.household_created": "ماڵەوە دروستکرا. کۆدەکە بدە بە هاوژوورەکانت.",
        "flash.password_required": "بۆ دڵنیابوونەوە وشەی نهێنی پێویستە.",
        "flash.password_incorrect": "وشەی نهێنی هەڵەیە.",
        "flash.admin_cant_leave": "وەک بەڕێوەبەر ناتوانیت ماڵەوە جێبهێڵیت.",
        "flash.settle_admin_only": "تەنها بەڕێوەبەرانی ماڵەوە دەتوانن یەکسانکردنەوە بکەن.",
        "flash.left_household": "ماڵەکەت جێهێشت.",
        "flash.delete_account_blocked": "پێش سڕینەوەی هەژمار، ئەندامەکانی تر لاببە یان ماڵەکە جێبهێڵە.",
        "flash.account_deleted": "هەژمارەکەت بەسەرکەوتوویی سڕایەوە.",
        "flash.enter_join_code": "تکایە کۆدی بەشداریکردن بنووسە.",
        "flash.already_in_this_household": "تۆ پێشتر لەم ماڵەوەیەیت.",
        "flash.switched_household": "گۆڕدرا بۆ ماڵەوەی: {name}",
        "flash.admin_cant_switch": "وەک بەڕێوەبەر ناتوانیت ماڵەکەت بگۆڕیت هەتا ئەندامانی تر مابن.",
        "flash.use_leave_household": "دوگمەی 'جێهێشتنی ماڵەوە' بەکاربهێنە بۆ لابردنی خۆت.",
        "flash.cant_remove_admin": "ناتوانیت بەڕێوەبەری سەرەکی ماڵەوە لاببەیت.",
        "flash.user_not_member": "ئەم بەکارهێنەرە ئەندامی ئەم ماڵەوەیە نییە.",
        "flash.member_removed": "ئەندامەکە لابرا.",
        "flash.household_name_empty": "ناوەکە نابێت بەتاڵ بێت.",
        "flash.household_name_updated": "ناوی ماڵەوە نوێکرایەوە.",
        "flash.title_required": "ناونیشان پێویستە.",
        "flash.amount_positive": "بڕی پارە دەبێت ژمارەیەکی دروست و پۆزەتیڤ بێت.",
        "flash.select_participant": "تکایە لانیکەم یەک کەس هەڵبژێرە کە سوودمەندە لە خەرجییەکە.",
        "flash.invalid_participants": "کەسە هەڵبژێردراوەکان هەڵەن.",
        "flash.expense_added": "خەرجییەکە زیادکرا.",
        "flash.only_payer_delete": "تەنها ئەو کەسەی پارەکەی داوە دەتوانێت ئەم خەرجییە بسڕێتەوە.",
        "flash.expense_deleted": "خەرجییەکە سڕایەوە.",
        "flash.nothing_to_settle": "هیچ خەرجییەکی چالاک نییە بۆ یەکسانکردنەوە.",
        "flash.settled_up": "هەموو شتێک یەکسانکرایەوە! خەرجییەکانی مانگی {month} ئەرشیفکران.",
        "household.default_name": "ماڵەوەی من",
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
        lang = (session.get("lang") or "en").lower()
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
        token = secrets.token_urlsafe(32)
        user.email_verification_token_hash = token_hash(token)
        user.email_verification_sent_at = datetime.utcnow()
        user.email_verified = False
        return token

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
            app.logger.info("Email not sent (MAIL_HOST not configured): to=%s subject=%s", to_email, subject)
            return False
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = app.config["MAIL_FROM"]
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

    def send_verification_email(user: User, token: str) -> bool:
        verify_url = build_external_url("verify_email", token=token)
        if not email_enabled():
            print(f"Email verification URL for {user.email}: {verify_url}")
            return False
        text_body = render_template(
            "emails/verify_email.txt",
            user=user,
            verify_url=verify_url,
            ttl_hours=app.config["EMAIL_VERIFICATION_TTL_HOURS"],
        )
        html_body = render_template(
            "emails/verify_email.html",
            user=user,
            verify_url=verify_url,
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

    dummy_password_hash = generate_password_hash("invalid-password")

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

    # ---------- Auth ----------
    @app.get("/register")
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("register.html")

    @app.post("/register")
    def register_post():
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        next_raw = request.args.get("next") or request.form.get("next")
        next_url = safe_next_url(next_raw, "")

        if not name or not email or not password or not confirm_password:
            flash(t("flash.fill_all_fields"), "error")
            return redirect(url_for("register", next=next_url) if next_url else url_for("register"))

        if password != confirm_password:
            flash(t("flash.passwords_no_match"), "error")
            return redirect(url_for("register", next=next_url) if next_url else url_for("register"))

        if not password_is_strong(password):
            flash(t("flash.password_too_weak", min_len=app.config["PASSWORD_MIN_LENGTH"]), "error")
            return redirect(url_for("register", next=next_url) if next_url else url_for("register"))

        if User.query.filter_by(email=email).first():
            flash(t("flash.email_registered"), "error")
            return redirect(url_for("login", next=next_url) if next_url else url_for("login"))

        u = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            email_verified=False,
        )
        verify_token = issue_email_verification(u)
        db.session.add(u)
        db.session.commit()
        send_verification_email(u, verify_token)
        flash(t("flash.verification_email_sent"), "success")
        session.permanent = True
        login_user(u, remember=True)
        if u.email_verified is not True:
            if next_url:
                session["post_verify_next"] = next_url
            return redirect(url_for("verify_required"))
        # Support invite flows (e.g., QR join) via ?next= or hidden form field
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
        if not u or not check_password_hash(u.password_hash, password):
            if not u:
                check_password_hash(dummy_password_hash, password)
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
        if not password_is_strong(new_password):
            flash(t("flash.password_too_weak", min_len=app.config["PASSWORD_MIN_LENGTH"]), "error")
            return redirect(url_for("reset_password", token=token))

        u.password_hash = generate_password_hash(new_password)
        u.password_reset_token_hash = None
        u.password_reset_sent_at = None
        u.password_reset_expires_at = None
        db.session.commit()
        flash(t("flash.password_reset_success"), "success")
        return redirect(url_for("login"))

    @app.get("/verify-email/<token>")
    def verify_email(token: str):
        token_hash_value = token_hash(token)
        u = User.query.filter_by(email_verification_token_hash=token_hash_value).first()
        if not u:
            flash(t("flash.verification_link_invalid"), "error")
            return redirect(url_for("login"))
        if not u.email_verification_sent_at:
            flash(t("flash.verification_link_invalid"), "error")
            return redirect(url_for("login"))

        expires_at = u.email_verification_sent_at + timedelta(
            hours=app.config["EMAIL_VERIFICATION_TTL_HOURS"]
        )
        if expires_at < datetime.utcnow():
            u.email_verification_token_hash = None
            u.email_verification_sent_at = None
            db.session.commit()
            flash(t("flash.verification_link_expired"), "error")
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
            if not check_password_hash(current_user.password_hash, current_password):
                flash(t("flash.current_password_incorrect"), "error")
                return redirect(redirect_to)
            if new_password != confirm_password:
                flash(t("flash.new_passwords_no_match"), "error")
                return redirect(redirect_to)
            if not password_is_strong(new_password):
                flash(t("flash.password_too_weak", min_len=app.config["PASSWORD_MIN_LENGTH"]), "error")
                return redirect(redirect_to)
            current_user.password_hash = generate_password_hash(new_password)

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
        return redirect(url_for("household"))

    @app.post("/setup-household/join")
    @login_required
    def join_household():
        hid = get_household_id_or_none()
        if hid:
            return redirect(url_for("household"))

        code = request.form.get("join_code", "").strip().upper()
        h = Household.query.filter_by(join_code=code).first()
        if not h:
            flash(t("flash.invalid_join_code"), "error")
            return redirect(url_for("setup_household"))

        db.session.add(Membership(user_id=current_user.id, household_id=h.id))
        db.session.commit()
        flash(t("flash.joined_household", name=h.name), "success")
        return redirect(url_for("dashboard"))

    @app.get("/household")
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
        can_leave = not is_owner
        leave_block_reason = t("flash.admin_cant_leave") if is_owner else None

        return render_template(
            "household.html",
            household=h,
            members=members,
            is_owner=is_owner,
            owner_id=h.owner_id,
            can_leave=can_leave,
            leave_block_reason=leave_block_reason,
        )

    @app.post("/household/leave")
    @login_required
    def leave_household():
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

        if h.owner_id == current_user.id:
            flash(t("flash.admin_cant_leave"), "error")
            return redirect(url_for("household"))

        # Remove membership
        Membership.query.filter_by(user_id=current_user.id).delete()  # defensive: clear any stray memberships

        db.session.commit()
        flash(t("flash.left_household"), "success")
        return redirect(url_for("setup_household"))

    @app.post("/account/delete")
    @login_required
    def delete_account():
        password = request.form.get("password", "")
        if not password or not check_password_hash(current_user.password_hash, password):
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
        exp = (
            Expense.query
            .filter_by(household_id=hid, is_archived=False)
            .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
            .all()
        )

        # payer names
        user_by_id = {u.id: u for u in members}

        participants = ExpenseParticipant.query.join(
            Expense, ExpenseParticipant.expense_id == Expense.id
        ).filter(Expense.household_id == hid, Expense.is_archived == False).all()

        parts_map = {}
        for p in participants:
            parts_map.setdefault(p.expense_id, []).append(p.user_id)

        today = datetime.now().strftime("%Y-%m-%d")
        return render_template(
            "expenses.html",
            members=members,
            expenses=exp,
            user_by_id=user_by_id,
            parts_map=parts_map,
            today=today,
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
        if not password or not check_password_hash(current_user.password_hash, password):
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
        sort = request.args.get("sort", "month").strip().lower() or "month"
        selected_month = request.args.get("month", "").strip()
        selected_settle = request.args.get("settle", "").strip()

        q = Expense.query.filter_by(household_id=hid, is_archived=True)
        if sort == "settle":
            if selected_settle:
                q = q.filter_by(archived_settle_id=selected_settle)
            archived = q.order_by(Expense.archived_settled_at.desc().nullslast(), Expense.expense_date.desc()).all()
        else:
            sort = "month"
            if selected_month:
                q = q.filter_by(archived_month=selected_month)
            archived = q.order_by(Expense.archived_month.desc().nullslast(), Expense.expense_date.desc()).all()

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
        for sid, smin, smax, _sat in settle_rows:
            if not sid or not smin or not smax:
                continue
            settles.append({
                "id": sid,
                "label": _fmt_settle_label(smin, smax),
                "start": smin,
                "end": smax,
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

        total_iqd = sum(e.amount_iqd for e in archived)

        return render_template(
            "archive.html",
            archived=archived,
            months=months,
            settles=settles,
            settle_label_by_id={s["id"]: s["label"] for s in settles},
            sort=sort,
            selected_month=selected_month,
            selected_settle=selected_settle,
            total_iqd=total_iqd,
            user_by_id=user_by_id,
            parts_map=parts_map,
            is_owner=is_owner,
        )

    return app

app = create_app()

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "init-db":
        init_db()
    else:
        # auto-create tables (safe for sqlite dev)
        with app.app_context():
            db.create_all()
        app.run(debug=True)
