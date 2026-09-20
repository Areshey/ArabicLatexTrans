import shutil
from typing import List, Dict, Any
import re
import os
import subprocess
from .utils import *

class LaTexCompiler:
    def __init__(self, output_latex_dir: str):
        self.output_latex_dir = output_latex_dir

    def compile(self):
        """
        Compile the LaTeX document .
        """
        tex_file_to_compile = find_main_tex_file(self.output_latex_dir)
        if not tex_file_to_compile:
            print("⚠️ Warning: There is no main tex file to compile in this directory.")
            return None
        print("Start compiling with pdflatex...⏳")
        compile_out_dir_pdflatex = os.path.join(self.output_latex_dir, "build_pdflatex")
        self._compile_with_pdflatex(tex_file_to_compile, compile_out_dir_pdflatex, engine="pdflatex")
        pdf_files = [os.path.join(compile_out_dir_pdflatex, file) for file in os.listdir(compile_out_dir_pdflatex) if file.lower().endswith('.pdf')]
        if pdf_files:

            print(f"✅  Successfully generated PDF file !") 
            return pdf_files[0]
        else:
            print(f"⚠️  Failed to generate PDF with pdflatex. 🔁Retrying with xelatex...⏳") 
            compile_out_dir_xelatex = os.path.join(self.output_latex_dir, "build_xelatex")
            self._compile_with_xelatex(tex_file_to_compile, compile_out_dir_xelatex, engine="xelatex")
            pdf_files = [os.path.join(compile_out_dir_xelatex, file) for file in os.listdir(compile_out_dir_xelatex) if file.lower().endswith('.pdf')]
            if pdf_files:
                print(f"✅  Successfully generated PDF file !") 
                return pdf_files[0]
            else:
                print(f"⚠️  Failed to generate PDF with xelatex. Please check the log.")
                log_files_xelatex = [os.path.join(compile_out_dir_xelatex, file) for file in os.listdir(compile_out_dir_xelatex) if file.lower().endswith('.log')]
                log_files_pdflatex = [os.path.join(compile_out_dir_pdflatex, file) for file in os.listdir(compile_out_dir_pdflatex) if file.lower().endswith('.log')]
                if log_files_xelatex and log_files_pdflatex:
                    print(f"📄 Log files for pdflatex: {log_files_pdflatex}")
                    print(f"📄 Log files for xelatex: {log_files_xelatex}")
                return None
    

    def compile_ja(self):
        """
        Compile the LaTeX document .
        """
        tex_file_to_compile = find_main_tex_file(self.output_latex_dir)
        if not tex_file_to_compile:
            print("⚠️ Warning: There is no main tex file to compile in this directory.")
            return None
        print("Start compiling with lualatex...⏳")
        compile_out_dir_lualatex = os.path.join(self.output_latex_dir, "build_lualatex")
        self._compile_with_lualatex(tex_file_to_compile, compile_out_dir_lualatex, engine="lualatex")
        pdf_files = [os.path.join(compile_out_dir_lualatex, file) for file in os.listdir(compile_out_dir_lualatex) if file.lower().endswith('.pdf')]
        if pdf_files:

            print(f"✅  Successfully generated PDF file !") 
            return pdf_files[0]
        else:
            print(f"⚠️  Failed to generate PDF with xelatex. Please check the log.")
            # log_files_xelatex = [os.path.join(compile_out_dir_xelatex, file) for file in os.listdir(compile_out_dir_xelatex) if file.lower().endswith('.log')]
            log_files_lualatex = [os.path.join(compile_out_dir_lualatex, file) for file in os.listdir(compile_out_dir_lualatex) if file.lower().endswith('.log')]
            if log_files_lualatex:
                print(f"📄 Log files for pdflatex: {log_files_lualatex}")
            return None
        
    def compile_ar(self):
        """
        Compile Arabic LaTeX documents using XeLaTeX,
        with LuaLaTeX as a fallback.
        """
        # Preserve LTR direction for citations in all Arabic .tex files (Updated by Imaan Alkhanen)
        for tex_file in find_tex_files(self.output_latex_dir):
            with open(tex_file, "r", encoding="utf-8") as f:
                latex_code = f.read()

            fixed_code = fix_citation_direction_for_arabic(latex_code)

            if fixed_code != latex_code:
                with open(tex_file, "w", encoding="utf-8") as f:
                    f.write(fixed_code)
                    
        tex_file_to_compile = find_main_tex_file(self.output_latex_dir)
        if not tex_file_to_compile:
            print("⚠️ Warning: There is no main tex file to compile.")
            return None

        print("Start compiling with xelatex...⏳")

        compile_out_dir_xelatex = os.path.join(
            self.output_latex_dir,
            "build_xelatex"
        )

        self._compile_with_xelatex(
            tex_file_to_compile,
            compile_out_dir_xelatex,
            engine="xelatex"
        )

        pdf_files = [
            os.path.join(compile_out_dir_xelatex, f)
            for f in os.listdir(compile_out_dir_xelatex)
            if f.lower().endswith(".pdf")
        ]

        if pdf_files:
            print("✅ Successfully generated PDF file!")
            return pdf_files[0]

        print("⚠️ XeLaTeX failed. Retrying with LuaLaTeX...⏳")

        compile_out_dir_lualatex = os.path.join(
            self.output_latex_dir,
            "build_lualatex"
        )

        self._compile_with_lualatex(
            tex_file_to_compile,
            compile_out_dir_lualatex,
            engine="lualatex"
        )

        pdf_files = [
            os.path.join(compile_out_dir_lualatex, f)
            for f in os.listdir(compile_out_dir_lualatex)
            if f.lower().endswith(".pdf")
        ]

        if pdf_files:
            print("✅ Successfully generated PDF file!")
            return pdf_files[0]

        print("⚠️ Failed to generate PDF for Arabic document.")

        return None

    def compile_source(self, pdf_dir):
        if pdf_dir is None:
            pdf_dir = self.output_latex_dir
        os.makedirs(pdf_dir, exist_ok=True)  # Ensure directory exists

        tex_file_to_compile = find_main_tex_file(self.output_latex_dir)
        if not tex_file_to_compile:
            print("⚠️ Warning: No main .tex file found in directory.")
            return None

        print("Start compiling with pdflatex...⏳")
        self._compile_with_pdflatex(
            tex_file_to_compile,
            out_dir=pdf_dir,  # Output directly to pdf_dir
            engine="pdflatex"
        )

        pdf_files = [
            f for f in os.listdir(pdf_dir)
            if f.lower().endswith('.pdf') and not f.startswith('._')  # Skip macOS temp files
        ]

        if pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_files[0])
            print(f"✅ Successfully generated PDF at: {pdf_path}")
            return pdf_path

        # Fallback to xelatex if pdflatex failed
        print("⚠️ pdflatex failed. Retrying with xelatex...⏳")
        self._compile_with_xelatex(
            tex_file_to_compile,
            out_dir=pdf_dir,  # Output directly to pdf_dir
            engine="xelatex"
        )

        pdf_files = [
            f for f in os.listdir(pdf_dir)
            if f.lower().endswith('.pdf') and not f.startswith('._')
        ]

        if pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_files[0])
            print(f"✅ Successfully generated PDF at: {pdf_path}")
            return pdf_path

        # If both compilers failed
        print("⚠️ Failed to generate PDF with both compilers.")
        log_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.log')]
        if log_files:
            print("📄 Compilation logs:")
            for log in log_files:
                print(f"  - {os.path.join(pdf_dir, log)}")

        return None

    def _compile_with_pdflatex(self,
                              tex_file: str, 
                              out_dir: str, 
                              engine: str = "pdflatex"):
        
        os.makedirs(out_dir, exist_ok=True)
        
        cmd = [
            "latexmk",
            f"-{engine}",                
            "-interaction=nonstopmode",   # no stop on errors
            f"-outdir={out_dir}",  
            f"-file-line-error",       
            f"-synctex=1",
            f"-f",                        # force mode
            tex_file
        ]
        cwd = os.path.dirname(tex_file)
        try:
            subprocess.run(cmd, check=True, capture_output=True, cwd=cwd)
            print("✅  Compilation successful!") #compile success!

            output_path = os.path.join(self.output_latex_dir, "success.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("Compilation successful\n")
                
        except subprocess.CalledProcessError as e:
            print("⚠️  Somthing went wrong during compiling with pdflatex.")

     #Preserve left-to-right (LTR) direction for bibliography entries (Updated by Imaan Alkhanen)
    # while keeping the Arabic bibliography heading unchanged. (Updated by Imaan Alkhanen)
    def _fix_bbl_direction_for_arabic(self, bbl_file: str):
        """
        Make bibliography entries LTR while keeping
        the Arabic bibliography heading unchanged.
        """

        if not os.path.exists(bbl_file):
            return

        with open(bbl_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Do not apply twice
        if r"\begin{LTR}" in content:
            return

        begin_marker = r"\begin{thebibliography}"
        end_marker = r"\end{thebibliography}"

        start = content.find(begin_marker)
        end = content.find(end_marker)

        if start == -1 or end == -1:
            return

        # Locate the end of \begin{thebibliography}{...}
        brace_start = content.find("{", start + len(begin_marker))

        if brace_start == -1:
            return

        depth = 1
        i = brace_start + 1

        while i < len(content) and depth > 0:
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
            i += 1

        if depth != 0:
            return

        content = (
            content[:i]
            + "\n\\begin{LTR}\n"
            + content[i:end]
            + "\n\\end{LTR}\n"
            + content[end:]
        )

        with open(bbl_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _compile_with_xelatex(
            self,
            tex_file: str,
            out_dir: str,
            engine: str = "xelatex"):

        os.makedirs(out_dir, exist_ok=True)
        cwd = os.path.dirname(tex_file)

        # Copy bibliography files to latexmk output directory
        for file in os.listdir(cwd):
            if file.lower().endswith(".bib"):
                src = os.path.join(cwd, file)
                dst = os.path.join(out_dir, file)
                shutil.copy2(src, dst)

        cmd = [
            "latexmk",
            f"-{engine}",
            "-interaction=nonstopmode",
            f"-outdir={out_dir}",
            "-file-line-error",
            "-synctex=1",
            "-f",
            tex_file
        ]

        try:
            # First run:
            # latexmk creates .aux, .bbl, citations, references, etc.
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                cwd=cwd
            )

        except subprocess.CalledProcessError as e:
            # With -f, latexmk may still create the PDF and .bbl
            # even when XeLaTeX returns code 1.
            print("⚠️ First XeLaTeX/latexmk run completed with errors.")
            print("=" * 80)
            print(e.stdout.decode(errors="ignore"))
            print("=" * 80)
            print(e.stderr.decode(errors="ignore"))

        # Get .bbl filename from the .tex filename
        #tex_name = os.path.splitext(os.path.basename(tex_file))[0]
        #bbl_file = os.path.join(out_dir, f"{tex_name}.bbl")

        # Fix bibliography direction after BibTeX has generated the .bbl
        #self._fix_bbl_direction_for_arabic(bbl_file)
        # Fix direction in all bibliography files generated by latexmk
        for file in os.listdir(out_dir):
            if file.lower().endswith(".bbl"):
                bbl_file = os.path.join(out_dir, file)
                self._fix_bbl_direction_for_arabic(bbl_file)

        # Second latexmk run:
        # Reads the modified .bbl and regenerates the PDF
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                cwd=cwd
            )

            print("✅ Compilation successful with xelatex!")

        except subprocess.CalledProcessError as e:
            print("⚠️ Something went wrong during final compiling with xelatex.")
            print("=" * 80)
            print(e.stdout.decode(errors="ignore"))
            print("=" * 80)
            print(e.stderr.decode(errors="ignore"))