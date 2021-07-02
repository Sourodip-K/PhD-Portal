import os
from flask import (render_template, send_file, request, session,
                    url_for, redirect, flash)
from flask_login import (current_user, login_user, 
                        logout_user, login_required)
from phdsubmission import db, bcrypt
from phdsubmission.models import User, Student, Professor, Request, Studymaterial
from flask import Blueprint
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def home():
    if current_user.professor:
        return redirect(url_for('main.admin'))
    professor_list = Professor.query.filter_by(approved = 'Y').all()
    return render_template('home.html', professor_list=professor_list)

# Route for Login
@main.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            if not current_user.professor:
                return redirect(url_for('main.home'))
        return render_template('login.html', title='Login')
    if request.method == 'POST':
        user = User.query.filter_by(email = request.form.get("email")).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get("password")):
            login_user(user)    
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Please Check your Email ID & Password')
            return redirect(url_for('main.login'))

# Route for Singup
@main.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('main.home'))
        return render_template('signup.html', title='Register')
    if request.method == 'POST':
        user = User.query.filter_by(email = request.form.get("email")).first()
        if not user:
            hashed_password = bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8')
            user = User(fullname=request.form.get("name"), email=request.form.get("email"), password=hashed_password)
            student = Student()
            student.user = user
            student.document = request.form.get("registration-document")
            db.session.add(user)
            db.session.add(student)
            db.session.commit()
            login_user(user)
            return redirect(url_for('main.home'))
        else:
            flash('Email Address Already exist!')
            return redirect(url_for('main.signup'))

# Route for Admin Singup
@main.route('/admin/signup', methods=['POST', 'GET'])
def admin_signup():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('main.home'))
        return render_template('admin-signup.html', title='Register Admin')
    if request.method == 'POST':
        user = User.query.filter_by(email = request.form.get("email")).first()
        if not user:
            hashed_password = bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8')
            user = User(fullname=request.form.get("name"), email=request.form.get("email"), password=hashed_password)
            professor = Professor()
            professor.user = user
            professor.specialization = request.form.get("specialization")
            professor.approved = 'N'
            db.session.add(user)
            db.session.add(professor)
            db.session.commit()
            flash('Profile Created Successfully. You can login now.')
            return redirect(url_for('main.login'))
        else:
            flash('Email Address Already exist!')
            return redirect(url_for('main.admin_signup'))

# Route for Admin Login
@main.route('/admin/login')
def admin_login():
    return redirect(url_for('main.login'))

# Route for Logout
@main.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('main.login'))

# Route for Admin Logout
@main.route('/admin/logout')
@login_required
def admin_logout():
    return redirect(url_for('main.logout'))

# Route for status
@main.route('/status')
@login_required
def status():
    return render_template('my-status.html', title='My Status', status=current_user.student.sid)

# Route for request
@main.route('/request/<req>')
@login_required
def phd_request(req):
    phd_req = Request.query.filter_by(sid = current_user.student.sid).first()
    if not phd_req:
        phd_new_request = Request()
        phd_new_request.student = current_user.student
        phd_new_request.pid = req
        phd_new_request.status = 'I'
        db.session.add(phd_new_request)
        db.session.commit()
        flash('Your request has been submitted successfully.')
    else:
        flash('You Already requested.')
    return redirect(url_for('main.status'))

@main.route('/admin/')
@login_required
def admin():
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    all_req = Request.query.filter(Request.pid == current_user.professor.pid).all()
    return render_template('admin.html', title='Admin', request_list=all_req)

# Route for request
@main.route('/change-status/<req_id>/<change_status>')
@login_required
def change_status_request(req_id, change_status):
    req = Request.query.filter_by(rid = req_id).first()
    if change_status == 'U':
        req.status = 'U'
    elif change_status == 'A':
        req.status = 'A'
    elif change_status == 'R':
        req.status = 'R'
    db.session.commit()
    return redirect(url_for('main.admin'))

# Route for Approve Professors
@main.route('/admin/approve-professors')
@login_required
def approve_professors():
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    prof_req = Professor.query.filter_by(approved='N').all()
    print(prof_req)
    return render_template('approve-professors.html', title='Approve Professors', prof_req=prof_req)

# Route for Approve Professor ID
@main.route('/admin/approve-professors/<pid>')
@login_required
def approve_professor_req(pid):
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    prof_req = Professor.query.filter_by(pid=pid).first()
    prof_req.approved = 'Y'
    db.session.commit()
    return redirect(url_for('main.approve_professors'))

# Route for Submit Thesis
@main.route('/submit-thesis', methods=['POST', 'GET'])
@login_required
def submit_thesis():
    if current_user.student.request and current_user.student.request.status == 'A' and not current_user.student.request.thesisStatus:
        submitted_thesis = request.files['thesis']
        _, f_ext = os.path.splitext(submitted_thesis.filename)
        thesis_filename = 'sid-' + str(current_user.student.sid) + f_ext
        thesis_path = os.path.join(os.path.dirname(main.root_path), 'static\\thesis', thesis_filename)
        submitted_thesis.save(thesis_path)
        current_user.student.request.thesisStatus = 'I'
        current_user.student.request.thesisfilename = thesis_filename
        db.session.commit()
    else:
        flash('You already submitted your thesis.')
    return redirect(url_for('main.status')) 

# Route for Thesis status
@main.route('/thesis-status')
@login_required
def thesis_status():
    return render_template('my-thesis-status.html', title='My Thesis Status')

# Route for Admin Thesis
@main.route('/admin/thesis')
@login_required
def admin_thesis():
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    all_thesis = Request.query.filter(Request.pid == current_user.professor.pid).filter(Request.status == 'A').filter(Request.thesisStatus != '').all()
    return render_template('admin-thesis.html', title='Submitted Thesis', all_thesis=all_thesis)

# Route for Change Thesis Status
@main.route('/admin/change-thesis-status/<req_id>/<change_status>')
@login_required
def change_thesis_status(req_id, change_status):
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    req = Request.query.filter_by(rid = req_id).first()
    if change_status == 'U':
        req.thesisStatus = 'U'
    elif change_status == 'R':
        req.thesisStatus = 'R'
    db.session.commit()
    return redirect(url_for('main.admin_thesis'))

# Route for Download Thesis
@main.route('/admin/download-thesis/<rid>')
@login_required
def download_admin_thesis(rid):
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    thesis_path = os.path.join(os.path.dirname(main.root_path), 'static\\thesis\\')
    file_path = thesis_path + Request.query.filter(Request.rid==rid).first().thesisfilename
    return send_file(file_path, as_attachment=True)

# Route for Accept thesis
@main.route('/admin/accept-thesis/<rid>', methods=['POST'])
@login_required
def accept_thesis(rid):
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    req = Request.query.filter(Request.rid == rid).first()
    req.thesisStatus = 'A'
    req.student.phdgrade = request.form.get("grade")
    db.session.commit()
    return redirect(url_for('main.admin_thesis'))

# Route for Admin Study Material
@main.route('/admin/study-material', methods=['POST', 'GET'])
@login_required
def admin_study_material():
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    if request.method == 'GET':
        smlist = Studymaterial.query.filter(Studymaterial.pid == current_user.professor.pid).order_by(Studymaterial.date.desc()).all()
        return render_template('admin-study-material.html', title='Study Material', smlist=smlist)        
    if request.method == 'POST':
        sm_attachment = request.files['study-material']
        study_material = Studymaterial()
        study_material.professor = current_user.professor
        study_material.smcontent = request.form.get('study-material-content')
        study_material.date = datetime.now()
        if sm_attachment:
            _, f_ext = os.path.splitext(sm_attachment.filename)
            sm_filename = 'pid-' + str(current_user.professor.pid) + '-' + str(datetime.now().strftime("%d-%m-%Y-%H-%M-%S")) + f_ext
            sm_path = os.path.join(os.path.dirname(main.root_path), 'static\\study-material', sm_filename)
            sm_attachment.save(sm_path)
            study_material.attachment = sm_filename
        db.session.add(study_material)
        db.session.commit()
    return redirect(url_for('main.admin_study_material'))

# Route for Delete Study Material
@main.route('/admin/delete-study-materia/<smid>')
@login_required
def delete_study_material(smid):
    if not current_user.professor:
        return redirect(url_for('main.home'))
    if current_user.professor.approved == 'N':
        flash('Please ask anyone from administration to Approve your profile')
        return redirect(url_for('main.login'))
    study_material = Studymaterial.query.filter(Studymaterial.smid == smid).first()
    if study_material.attachment:
        try:
            delete_file(study_material.attachment)
        except:
            print('Error in Deleting Attachment')
    db.session.delete(study_material)
    db.session.commit()
    return redirect(url_for('main.admin_study_material')) 
    
def delete_file(filename):
    filepath = os.path.join(os.path.dirname(main.root_path), 'static\\study-material', filename)
    os.remove(filepath)

# Route for Download Study Material
@main.route('/download-study-material/<smid>')
@login_required
def download_study_material(smid):
    sm_path = os.path.join(os.path.dirname(main.root_path), 'static\\study-material\\')
    file_path = sm_path + Studymaterial.query.filter(Studymaterial.smid==smid).first().attachment
    return send_file(file_path, as_attachment=True)

# Route for Student Study Material
@main.route('/study-material')
@login_required
def study_material():
    if current_user.professor:
        return redirect(url_for('main.admin_study_material'))
    smlist = []
    if current_user.student.request:        
        if current_user.student.request.status == 'A':
            smlist = Studymaterial.query.filter(Studymaterial.pid == current_user.student.request.pid).order_by(Studymaterial.date.desc()).all()
    return render_template('study-material.html', title='Study Material', smlist=smlist)        