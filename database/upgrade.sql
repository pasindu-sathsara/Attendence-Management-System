-- Select your existing database in Workbench before running this script. setup.py uses config.json.
ALTER TABLE class_session MODIFY COLUMN email varchar(255) NULL;
SET @change = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='student' AND column_name='must_change_password')=0, 'ALTER TABLE student ADD COLUMN must_change_password TINYINT NOT NULL DEFAULT 1', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='lecturer' AND column_name='must_change_password')=0, 'ALTER TABLE lecturer ADD COLUMN must_change_password TINYINT NOT NULL DEFAULT 1', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='ar_user' AND column_name='must_change_password')=0, 'ALTER TABLE ar_user ADD COLUMN must_change_password TINYINT NOT NULL DEFAULT 1', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='class_session' AND column_name='updated_by')=0, 'ALTER TABLE class_session ADD COLUMN updated_by VARCHAR(255) NULL', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='course_offering' AND column_name='teaching_end')=0, 'ALTER TABLE course_offering ADD COLUMN teaching_end DATE NULL', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='student' AND constraint_name='chk_student_batch')>0, 'ALTER TABLE student DROP CHECK chk_student_batch', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='student' AND column_name='batch')>0, 'ALTER TABLE student DROP COLUMN batch', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='ar_user' AND constraint_name='chk_ar_title')>0, 'ALTER TABLE ar_user DROP CHECK chk_ar_title', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
UPDATE ar_user SET title=NULL WHERE title='Ven';
UPDATE lecturer SET title=NULL WHERE title='Ven';
ALTER TABLE ar_user ADD CONSTRAINT chk_ar_title CHECK (title IN ('Mr','Mrs','Ms'));
SET @change = IF((SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='lecturer' AND constraint_name='chk_lecturer_type')>0, 'ALTER TABLE lecturer DROP CHECK chk_lecturer_type', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
ALTER TABLE lecturer ADD CONSTRAINT chk_lecturer_type CHECK (type IN ('Lecturer','Visiting Lecturer','Demonstrator','Temporary Lecturer','Coordinator','Senior Lecturer','Assistant Lecturer'));
SET @change = IF((SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='student_class_session' AND constraint_name='chk_absent_reason')>0, 'ALTER TABLE student_class_session DROP CHECK chk_absent_reason', 'SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
ALTER TABLE student_class_session ADD CONSTRAINT chk_absent_reason CHECK (absent_reason IN ('MC','SMC','SRC','EXCUSE'));
CREATE TABLE IF NOT EXISTS student_course (
 email varchar(255) NOT NULL,
 course_code varchar(20) NOT NULL,
 academic_year varchar(9) NOT NULL,
 PRIMARY KEY (email,course_code,academic_year),
 CONSTRAINT fk_student_course_student FOREIGN KEY (email) REFERENCES student(email),
 CONSTRAINT fk_student_course_offering FOREIGN KEY (course_code,academic_year) REFERENCES course_offering(course_code,academic_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS module_coordinator (
 email varchar(255) NOT NULL,
 visiting_email varchar(255) NOT NULL,
 course_code varchar(20) NOT NULL,
 academic_year varchar(9) NOT NULL,
 PRIMARY KEY (visiting_email,course_code,academic_year),
 FOREIGN KEY (email) REFERENCES lecturer(email),
 FOREIGN KEY (visiting_email,course_code,academic_year) REFERENCES lecturer_course(email,course_code,academic_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE IF NOT EXISTS attendance_audit (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 student_email varchar(255) NOT NULL,
 course_code varchar(20) NOT NULL,
 academic_year varchar(9) NOT NULL,
 session_date DATE NOT NULL,
 week_number TINYINT NOT NULL,
 old_status varchar(20) NOT NULL,
 new_status varchar(20) NOT NULL,
 updated_by varchar(255) NOT NULL,
 actor_email varchar(255) NOT NULL,
 updated_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX (course_code,academic_year,session_date,week_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
