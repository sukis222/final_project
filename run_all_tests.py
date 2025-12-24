import shutil
import subprocess
import sys
from pathlib import Path


def run_tests():
    """Запускает все тесты с отчетом о покрытии."""
    project_root = Path(__file__).parent

    for item in ['.coverage', '.pytest_cache', 'htmlcov', '__pycache__']:
        path = project_root / item
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    cmd = [
        sys.executable, '-m', 'pytest',
        'tests',
        '-v',
        '--tb=short',
        '--cov=.',
        '--cov-config=.coveragerc',
        '--cov-report=term',
        '--cov-report=html',
        '--cov-report=json:coverage.json',
        '-p', 'no:warnings',
    ]

    print(f"{' '.join(cmd)}")
    print('=' * 80)

    result = subprocess.run(cmd, cwd=project_root)

    print('\n' + '=' * 80)

    if result.returncode == 0:
        print('Все тесты прошли успешно!')
    else:
        print(f'Тесты завершились с ошибкой (код: {result.returncode})')

    print('\n Итоговый отчет о покрытии:')
    subprocess.run([
        sys.executable, '-m', 'coverage', 'report'
    ], cwd=project_root)

    html_report = project_root / 'htmlcov' / 'index.html'
    if html_report.exists():
        print(f'\nПодробный HTML отчет: {html_report}')

    return result.returncode


if __name__ == '__main__':
    sys.exit(run_tests())
