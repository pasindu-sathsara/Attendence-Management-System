-- Run once on the database matching 1407DBFinal.sql. Keeps existing records.
USE student_attendance_system;
CREATE TABLE IF NOT EXISTS student_course (
 email varchar(255) NOT NULL,
 course_code varchar(20) NOT NULL,
 academic_year varchar(9) NOT NULL,
 PRIMARY KEY (email,course_code,academic_year),
 CONSTRAINT fk_student_course_student FOREIGN KEY (email) REFERENCES student(email),
 CONSTRAINT fk_student_course_offering FOREIGN KEY (course_code,academic_year) REFERENCES course_offering(course_code,academic_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
