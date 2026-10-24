-- Existing installation: keeps all accounts, enrolments and attendance.
USE student_attendance_system;
CREATE TABLE IF NOT EXISTS student_course (
 email varchar(255) NOT NULL,
 course_code varchar(20) NOT NULL,
 academic_year varchar(9) NOT NULL,
 PRIMARY KEY (email,course_code,academic_year),
 CONSTRAINT fk_student_course_student FOREIGN KEY (email) REFERENCES student(email),
 CONSTRAINT fk_student_course_offering FOREIGN KEY (course_code,academic_year) REFERENCES course_offering(course_code,academic_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
ALTER TABLE class_session MODIFY COLUMN email varchar(255) NULL;
SET @change = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='student' AND column_name='batch')=0,
 'ALTER TABLE student ADD COLUMN batch varchar(5) NULL','SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='student' AND constraint_name='chk_student_batch')=0,
 'ALTER TABLE student ADD CONSTRAINT chk_student_batch CHECK (batch IS NULL OR batch REGEXP ''^[0-9]{2}/[0-9]{2}$'')','SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
SET @change = IF((SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='ar_user' AND constraint_name='chk_ar_title')>0,
 'ALTER TABLE ar_user DROP CHECK chk_ar_title','SELECT 1');
PREPARE change_statement FROM @change;
EXECUTE change_statement;
DEALLOCATE PREPARE change_statement;
ALTER TABLE ar_user ADD CONSTRAINT chk_ar_title CHECK (title IN ('Mr','Mrs','Ms','Ven'));
